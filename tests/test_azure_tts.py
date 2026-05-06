import os

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("CHATGOD_SKIP_TTS", "1")

from azure_text_to_speech import AzureTTSManager


def test_build_ssml_escapes_user_chat_text_and_preserves_case():
    manager = AzureTTSManager()

    ssml = manager.build_ssml("Tom & <Jerry>", "en-US-DavisNeural", "cheerful")

    assert "Tom &amp; &lt;Jerry&gt;" in ssml
    assert "Tom & <Jerry>" not in ssml


def test_build_ssml_uses_prefix_without_speaking_prefix():
    manager = AzureTTSManager()

    ssml = manager.build_ssml("(angry) Keep My Case", "en-US-DavisNeural", "random")

    assert "style='angry'" in ssml
    assert "Keep My Case" in ssml
    assert "(angry)" not in ssml
