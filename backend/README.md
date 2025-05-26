# Backend Service

This Node.js/Express service acts as the central hub for the voice assistant.

## Responsibilities

*   Receives audio streams from clients (Web UI, RPi, ESP32) via WebSocket.
*   Forwards audio to the `whisper-api` for Speech-to-Text (STT).
*   Sends the transcribed text to the configured n8n webhook URL (`N8N_WEBHOOK_URL`).
*   Receives the final text response back from n8n (after LLM processing).
*   Forwards the response text to the `coqui-tts-api` for Text-to-Speech (TTS).
*   Streams the synthesized audio response back to the originating client.

## Configuration

Configuration is primarily done via environment variables set in the main `.env` file or `docker-compose.yml`:

*   `BACKEND_PORT`: The port the backend server listens on (default: 3000).
*   `N8N_WEBHOOK_URL`: The full URL of your n8n workflow webhook that receives the transcribed text.
*   `WHISPER_API_URL`: (Optional, defaults internally) URL for the Whisper API service.
*   `COQUI_TTS_API_URL`: (Optional, defaults internally) URL for the Coqui TTS API service.