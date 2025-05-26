# Raspberry Pi Voice Assistant Client

This is the Raspberry Pi-based client for the local voice assistant system. It listens for the wake word "hey assistant", then streams audio to the backend server for processing.

## Features

- Wake word detection using Vosk (open source, no API keys required)
- Audio streaming via WebSockets
- Clean command-line interface with status indicators
- Manual trigger option (Enter key) as fallback
- Auto-reconnect to backend server
- Automatic stop after a configurable period of silence (defaults to ~2 seconds, see `SILENCE_THRESHOLD` and `SILENCE_DURATION_SEC` in `client.py`)

## Requirements

- Raspberry Pi (3 or newer recommended)
- USB microphone or sound card with microphone input
- Speaker/headphones for audio output
- Python 3.7 or newer
- Internet connection for initial setup (package installation)

## Installation

1. Install system dependencies:
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-pyaudio portaudio19-dev
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. For wake word detection, install Vosk:
   ```bash
   pip install vosk
   ```

4. Download a small Vosk model (only needed once):
   ```bash
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   ```

## Configuration

Configure the client by either:

1. Setting environment variables:
   ```bash
   export WEBSOCKET_URL="ws://YOUR_BACKEND_IP:3000"
   # Or specify components separately
   export BACKEND_HOST_IP="192.168.1.100"
   export BACKEND_PORT="3000"
   ```

2. Or creating a `.env` file in the same directory as client.py:
   ```
   WEBSOCKET_URL=ws://YOUR_BACKEND_IP:3000
   # Or specify components separately
   BACKEND_HOST_IP=192.168.1.100
   BACKEND_PORT=3000
   ```

## Usage

Run the client:
```bash
python client.py
```

The client will:
1. Connect to the backend server
2. Listen for the wake word "hey assistant"
3. Record your voice command after wake word detection
4. Stream the audio to the backend for processing
5. Play back the response
6. Return to listening for the wake word

You can also press Enter to manually trigger recording when wake word detection is not working or disabled.

## Troubleshooting

- **Connection Issues**: Make sure the BACKEND_HOST_IP is correctly set to your Docker host's actual IP address on your network (not localhost/127.0.0.1)
- **Audio Problems**: Check that your microphone and speakers are properly connected and configured
- **Wake Word Detection Issues**: 
  - Ensure you have downloaded the Vosk model and it's correctly located
  - Try adjusting the WAKE_WORD_SENSITIVITY value in client.py
  - Use the Enter key as a fallback if detection is unreliable
- **Missing/Unavailable Modules**: Verify all dependencies are properly installed

## Related Documentation

For complete system setup and architecture details, see:
- [Main Project README](../readme.md) - System overview and setup
- [ESP32 Client README](../esp32_client/README.md) - Alternative hardware client option
- [Hardware Setup Guide](../esp32_client/HARDWARE_SETUP.md) - Details on ESP32 hardware connections