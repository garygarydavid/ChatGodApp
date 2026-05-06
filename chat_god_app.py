from __future__ import annotations

from datetime import datetime, timezone
import os

from flask import Flask, render_template
from flask_socketio import SocketIO

from chat_core import ChatGodController, ChatMessage
from voices_manager import TTSManager

KICK_CHANNEL_NAME = os.getenv("KICK_CHANNEL_NAME", "garydavid")

app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")
controller: ChatGodController | None = None


def emit_event(event):
    if not event:
        return
    event_type = event.get("type")
    payload = {k: v for k, v in event.items() if k != "type"}
    socketio.emit(event_type, payload)


def emit_events(events):
    for event in events or []:
        emit_event(event)


def emit_status(message, level="info", source="app"):
    emit_event({"type": "status", "message": message, "level": level, "source": source})


@app.route("/")
def home():
    return render_template('index.html', kick_channel=KICK_CHANNEL_NAME, kick_chatroom_id=os.getenv("KICK_CHATROOM_ID", ""))


@socketio.event
def connect():
    emit_status("Browser connected to ChatGodApp.", "info", "socket")
    emit_status(f"Waiting for Kick chat from kick.com/{KICK_CHANNEL_NAME}.", "info", "kick")


@socketio.on("kick_status")
def kick_status(value):
    value = value or {}
    emit_status(str(value.get("message") or value.get("state") or "Kick status update."), str(value.get("level") or "info"), "kick")


@socketio.on("kick_message")
def kick_message(value):
    if controller is None:
        emit_status("Chat controller is not ready.", "error")
        return
    value = value or {}
    author = str(value.get("author") or value.get("sender") or "").strip()
    content = str(value.get("text") or value.get("content") or "").strip()
    if not author or not content:
        emit_status("Ignored malformed Kick chat message.", "warning", "kick")
        return
    emit_events(controller.process_chat_message(ChatMessage(author=author, content=content, timestamp=datetime.now(timezone.utc))))


@socketio.on("tts")
def toggletts(value):
    if controller is None:
        emit_status("Chat controller is not ready.", "error")
        return
    value = value or {}
    emit_event(controller.set_tts_enabled(value.get('user_number'), value.get('checked')))


@socketio.on("pickrandom")
def pickrandom(value):
    if controller is None:
        emit_status("Chat controller is not ready.", "error")
        return
    value = value or {}
    emit_event(controller.random_user(value.get('user_number')))


@socketio.on("choose")
def chooseuser(value):
    if controller is None:
        emit_status("Chat controller is not ready.", "error")
        return
    value = value or {}
    emit_event(controller.choose_user(value.get('user_number'), value.get('chosen_user')))


@socketio.on("voicename")
def choose_voice_name(value):
    if controller is None:
        emit_status("Chat controller is not ready.", "error")
        return
    value = value or {}
    emit_event(controller.update_voice_name(value.get('user_number'), value.get('voice_name')))


@socketio.on("voicestyle")
def choose_voice_style(value):
    if controller is None:
        emit_status("Chat controller is not ready.", "error")
        return
    value = value or {}
    emit_event(controller.update_voice_style(value.get('user_number'), value.get('voice_style')))


def create_controller():
    tts_manager = TTSManager()
    return ChatGodController(tts_manager=tts_manager, async_tts=True, status_callback=emit_event)


if __name__ == '__main__':
    controller = create_controller()
    emit_status(f"ChatGodApp configured for Kick channel: {KICK_CHANNEL_NAME}", "info", "kick")
    socketio.run(app, allow_unsafe_werkzeug=True)
