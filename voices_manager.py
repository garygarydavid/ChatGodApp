import os

from audio_player import AudioManager
from obs_websockets import OBSWebsocketsManager
from azure_text_to_speech import AzureTTSManager


class TTSManager:
    def __init__(self):
        self.azuretts_manager = AzureTTSManager()
        self.audio_manager = AudioManager()
        self.obswebsockets_manager = OBSWebsocketsManager()
        self.user_voice_names = {
            "1": "en-US-DavisNeural",
            "2": "en-US-TonyNeural",
            "3": "en-US-JaneNeural",
        }
        self.user_voice_styles = {"1": "random", "2": "random", "3": "random"}

        if os.getenv('CHATGOD_SKIP_TTS') == '1' or os.getenv('CHATGOD_SKIP_STARTUP_TTS') == '1':
            print("CHATGOD_SKIP_TTS/CHATGOD_SKIP_STARTUP_TTS set; skipping startup TTS for local smoke test.")
            return
        try:
            file_path = self.azuretts_manager.text_to_audio("Chat God App is now running!")
            if file_path:
                self.audio_manager.play_audio(file_path, True, True, True)
        except Exception as exc:
            print(f"Startup TTS failed; continuing without startup sound: {exc}")

    def update_voice_name(self, user_number, voice_name):
        if str(user_number) in self.user_voice_names and voice_name:
            self.user_voice_names[str(user_number)] = voice_name
        
    def update_voice_style(self, user_number, voice_style):
        if str(user_number) in self.user_voice_styles and voice_style:
            self.user_voice_styles[str(user_number)] = voice_style

    def text_to_audio(self, text, user_number):
        user_number = str(user_number)
        if os.getenv('CHATGOD_SKIP_TTS') == '1':
            print(f"CHATGOD_SKIP_TTS=1 set; skipping TTS for user {user_number}: {text}")
            return

        voice_name = self.user_voice_names.get(user_number, "random")
        voice_style = self.user_voice_styles.get(user_number, "random")

        try:
            tts_file = self.azuretts_manager.text_to_audio(text, voice_name, voice_style)
            if tts_file is None:
                return

            self.obswebsockets_manager.set_filter_visibility("Line In", f"Audio Move - DnD Player {user_number}", True)
            self.audio_manager.play_audio(tts_file, True, True, True)
            self.obswebsockets_manager.set_filter_visibility("Line In", f"Audio Move - DnD Player {user_number}", False)
        except Exception as exc:
            print(f"TTS failed for player {user_number}: {exc}")
