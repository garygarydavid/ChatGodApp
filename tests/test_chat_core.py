from datetime import datetime, timezone

from chat_core import ChatGodController, ChatMessage


class FakeTTS:
    def __init__(self):
        self.calls = []
        self.voice_names = []
        self.voice_styles = []

    def text_to_audio(self, text, user_number):
        self.calls.append((text, user_number))

    def update_voice_name(self, user_number, voice_name):
        self.voice_names.append((user_number, voice_name))

    def update_voice_style(self, user_number, voice_style):
        self.voice_styles.append((user_number, voice_style))


def test_choose_user_rejects_empty_names():
    controller = ChatGodController(tts_manager=FakeTTS())

    event = controller.choose_user("1", "   ")

    assert event["type"] == "status"
    assert event["level"] == "warning"
    assert controller.current_users["1"] is None


def test_kick_join_command_adds_user_to_correct_pool_case_insensitive():
    controller = ChatGodController(tts_manager=FakeTTS())
    message = ChatMessage(author="GaryFan", content="!PLAYER2", timestamp=datetime.now(timezone.utc))

    events = controller.process_chat_message(message)

    assert "garyfan" in controller.user_pools["2"]
    assert events[0]["type"] == "status"
    assert "joined player 2" in events[0]["message"]


def test_selected_kick_user_message_emits_message_and_tts_call():
    tts = FakeTTS()
    controller = ChatGodController(tts_manager=tts)
    controller.choose_user("1", "GaryFan")

    events = controller.process_chat_message(ChatMessage(author="garyfan", content="Hello Kick!", timestamp=datetime.now(timezone.utc)))

    assert {"type": "message_send", "user_number": "1", "current_user": "garyfan", "message": "Hello Kick!"} in events
    assert tts.calls == [("Hello Kick!", "1")]


def test_random_user_empty_pool_returns_visible_status_instead_of_silent_failure():
    controller = ChatGodController(tts_manager=FakeTTS())

    event = controller.random_user("3")

    assert event["type"] == "status"
    assert event["level"] == "warning"
    assert "No eligible users" in event["message"]


def test_malformed_user_number_is_rejected():
    controller = ChatGodController(tts_manager=FakeTTS())

    event = controller.choose_user("9", "somebody")

    assert event["type"] == "status"
    assert event["level"] == "error"
