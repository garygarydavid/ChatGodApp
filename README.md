# ChatGodApp

Written by DougDoug, with help from Banana. Adapted here for GaryDavid's Kick channel.

## SETUP

1) Python

The original app was written for Python 3.9.2. It now also includes compatibility for newer Python versions such as Python 3.13.

2) Install dependencies

```bash
pip install -r requirements.txt
```

If your system Python does not have pip/venv support, `uv` works well:

```bash
uv venv
. .venv/bin/activate
uv pip install -r requirements.txt
```

3) Kick chat

This version uses public Kick chat, not Twitch. The default Kick channel is:

```txt
garydavid
```

You can override it with:

```bash
KICK_CHANNEL_NAME='garydavid'
```

Kick chat is resolved in the browser and connected through Kick's public Pusher websocket channel. No Twitch token is needed.

4) Azure Text-to-Speech

This uses Microsoft Azure's TTS service for the text-to-speech voices.

Set these environment variables for real TTS:

```bash
AZURE_TTS_KEY='your-key'
AZURE_TTS_REGION='your-region'
```

For local UI testing without Azure/audio hardware, use:

```bash
CHATGOD_SKIP_TTS=1
```

5) OBS WebSockets

OBS integration is optional. If OBS is not connected, the app can continue with OBS disabled.

Optional OBS variables:

```bash
OBS_WEBSOCKET_HOST='localhost'
OBS_WEBSOCKET_PORT='4455'
OBS_WEBSOCKET_PASSWORD='your-password'
```

For local testing without OBS:

```bash
CHATGOD_ALLOW_NO_OBS=1
```

## LOCAL SMOKE TEST

```bash
cd /opt/data/projects/ChatGodApp
. .venv/bin/activate
SDL_AUDIODRIVER=dummy \
XDG_RUNTIME_DIR=/tmp \
CHATGOD_ALLOW_NO_OBS=1 \
CHATGOD_SKIP_TTS=1 \
KICK_CHANNEL_NAME='garydavid' \
python chat_god_app.py
```

Then open:

```txt
http://127.0.0.1:5000
```

This verifies that the Flask/Socket.IO UI starts. Full live chat requires the browser to be able to access Kick's public channel endpoint and websocket. If Kick blocks automatic channel lookup in your environment, set `KICK_CHATROOM_ID` to a known Kick chatroom id and the browser will skip the lookup step.

## BASIC APP USAGE

1) Run `chat_god_app.py` and open `http://127.0.0.1:5000` in a browser or OBS browser source.

2) Viewers join the pool of potential players by typing `!player1`, `!player2`, or `!player3` in Kick chat.

3) Click Pick Random to pick one viewer from the matching player pool.

4) You can manually assign a user by typing their Kick username into a Choose User field and pressing Enter.

5) Once a user is picked, their Kick chat messages will be shown in the UI and read out loud via Azure TTS when TTS is enabled.

6) Voice and voice style can be changed with the dropdowns. Messages can also start with one of these prefixes to choose a style:

```txt
(angry), (cheerful), (excited), (hopeful), (sad), (shouting), (shout), (terrified), (unfriendly), (whispering), (whisper), (random)
```

## TESTS

```bash
. .venv/bin/activate
pytest tests -q
```
