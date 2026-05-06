from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from queue import Queue
from threading import Lock, Thread
import traceback
from typing import Any, Callable

VALID_USER_NUMBERS = {"1", "2", "3"}


@dataclass(frozen=True)
class ChatMessage:
    author: str
    content: str
    timestamp: datetime | None = None


class TTSWorker:
    def __init__(self, tts_manager: Any, status_callback: Callable[[dict[str, Any]], None] | None = None):
        self.tts_manager = tts_manager
        self.status_callback = status_callback
        self.queue: Queue[tuple[str, str]] = Queue()
        self.thread = Thread(target=self._run, daemon=True, name="chatgod-tts-worker")
        self.thread.start()

    def submit(self, text: str, user_number: str) -> None:
        self.queue.put((text, user_number))

    def _run(self) -> None:
        while True:
            text, user_number = self.queue.get()
            try:
                self.tts_manager.text_to_audio(text, user_number)
            except Exception as exc:  # keep one bad TTS job from killing chat handling
                traceback.print_exc()
                if self.status_callback:
                    self.status_callback({
                        "type": "status",
                        "source": "tts",
                        "level": "error",
                        "message": f"TTS failed for player {user_number}: {exc}",
                    })
            finally:
                self.queue.task_done()


class ChatGodController:
    def __init__(self, tts_manager: Any | None = None, async_tts: bool = False, status_callback: Callable[[dict[str, Any]], None] | None = None):
        self.current_users = {"1": None, "2": None, "3": None}
        self.tts_enabled = {"1": True, "2": True, "3": True}
        self.user_pools: dict[str, dict[str, datetime]] = {"1": {}, "2": {}, "3": {}}
        self.keyphrases = {"1": "!player1", "2": "!player2", "3": "!player3"}
        self.seconds_active = 450
        self.max_users = 2000
        self.tts_manager = tts_manager
        self._lock = Lock()
        self.tts_worker = TTSWorker(tts_manager, status_callback) if async_tts and tts_manager is not None else None

    def status(self, message: str, level: str = "info", source: str = "app") -> dict[str, Any]:
        return {"type": "status", "source": source, "level": level, "message": message}

    def _valid_user_number(self, user_number: Any) -> str | None:
        user_number = str(user_number or "")
        return user_number if user_number in VALID_USER_NUMBERS else None

    def choose_user(self, user_number: Any, chosen_user: Any) -> dict[str, Any]:
        user_number = self._valid_user_number(user_number)
        if user_number is None:
            return self.status("Invalid player number.", "error")
        chosen_user = str(chosen_user or "").strip().lower()
        if not chosen_user:
            return self.status(f"Choose User for player {user_number} cannot be empty.", "warning")
        with self._lock:
            self.current_users[user_number] = chosen_user
        return {
            "type": "message_send",
            "message": f"{chosen_user} was picked!",
            "current_user": chosen_user,
            "user_number": user_number,
        }

    def set_tts_enabled(self, user_number: Any, checked: Any) -> dict[str, Any]:
        user_number = self._valid_user_number(user_number)
        if user_number is None:
            return self.status("Invalid player number.", "error")
        enabled = bool(checked)
        with self._lock:
            self.tts_enabled[user_number] = enabled
        return self.status(f"TTS {user_number} {'enabled' if enabled else 'disabled'}.", "info", "tts")

    def update_voice_name(self, user_number: Any, voice_name: Any) -> dict[str, Any]:
        user_number = self._valid_user_number(user_number)
        voice_name = str(voice_name or "").strip()
        if user_number is None or not voice_name:
            return self.status("Invalid voice name update.", "error")
        if self.tts_manager is not None:
            self.tts_manager.update_voice_name(user_number, voice_name)
        return self.status(f"Voice name updated for player {user_number}.", "info", "tts")

    def update_voice_style(self, user_number: Any, voice_style: Any) -> dict[str, Any]:
        user_number = self._valid_user_number(user_number)
        voice_style = str(voice_style or "").strip()
        if user_number is None or not voice_style:
            return self.status("Invalid voice style update.", "error")
        if self.tts_manager is not None:
            self.tts_manager.update_voice_style(user_number, voice_style)
        return self.status(f"Voice style updated for player {user_number}.", "info", "tts")

    def random_user(self, user_number: Any) -> dict[str, Any]:
        user_number = self._valid_user_number(user_number)
        if user_number is None:
            return self.status("Invalid player number.", "error")
        with self._lock:
            self._prune_pool(user_number)
            users = list(self.user_pools[user_number].keys())
            if not users:
                return self.status(f"No eligible users in pool for TTS {user_number}.", "warning")
            import random
            picked = random.choice(users)
            self.current_users[user_number] = picked
        return {
            "type": "message_send",
            "message": f"{picked} was picked!",
            "current_user": picked,
            "user_number": user_number,
        }

    def process_chat_message(self, message: ChatMessage) -> list[dict[str, Any]]:
        author = str(message.author or "").strip().lower()
        content = str(message.content or "")
        if not author or not content:
            return []
        timestamp = message.timestamp or datetime.now(timezone.utc)
        events: list[dict[str, Any]] = []
        lower_content = content.lower().strip()
        with self._lock:
            for user_number, keyphrase in self.keyphrases.items():
                if lower_content == keyphrase:
                    self.user_pools[user_number][author] = timestamp
                    self._prune_pool(user_number)
                    events.append(self.status(f"{author} joined player {user_number} pool.", "info", "kick"))
            selected = [n for n, username in self.current_users.items() if username == author]
            tts_flags = {n: self.tts_enabled[n] for n in selected}
        for user_number in selected:
            events.append({
                "type": "message_send",
                "message": content,
                "current_user": author,
                "user_number": user_number,
            })
            if tts_flags[user_number]:
                self._play_tts(content, user_number)
        return events

    def _play_tts(self, content: str, user_number: str) -> None:
        if self.tts_worker is not None:
            self.tts_worker.submit(content, user_number)
        elif self.tts_manager is not None:
            self.tts_manager.text_to_audio(content, user_number)

    def _prune_pool(self, user_number: str) -> None:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(seconds=self.seconds_active)
        pool = self.user_pools[user_number]
        for username, ts in list(pool.items()):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < threshold:
                pool.pop(username, None)
        while len(pool) > self.max_users:
            first = next(iter(pool))
            pool.pop(first, None)
