# Local Voice Assistant Project

*Last updated: May 27, 2025*

A completely local, privacy-focused voice assistant system (similar to a "private Alexa") that keeps all data processing within your own network.

## System Overview

This project creates a multi-component voice assistant system that runs entirely in your local network:

1.  **Client Devices** (choose one):
    *   **Raspberry Pi** with wake word detection via Vosk ("hey assistant")
    *   **ESP32** with local wake word detection via ESP-SR/WakeNet ("hey assistant")
    *   **Web UI** for browser-based interaction

2.  **Backend Services** (running in Docker):
    *   **Node.js/Express Backend**: The central orchestrator. Handles audio streaming from clients, sends audio to the Speech-to-Text (STT) service, routes transcribed text to the n8n workflow, receives the processed response, sends text to the Text-to-Speech (TTS) service, and streams synthesized audio back to the client.
    *   **Web UI Server**: A simple Nginx server to host the static files for the browser-based client.
    *   **Whisper API**: Custom Speech-to-Text service using OpenAI's Whisper model for accurate transcription.
    *   **Coqui TTS API**: Custom Text-to-Speech service using Coqui TTS. Supports standard TTS models and advanced XTTS models for voice cloning.

3.  **Required External Services** (running locally):
   - **Large Language Model**: Powers the assistant's intelligence (via Ollama or LM Studio)
   - **n8n Workflow Engine**: Orchestrates the interaction between components (Backend -> LLM -> Backend)

## Data Flow

1. Client captures audio after wake word detection or button press
2. Audio streams to backend service
3. Backend converts audio to text using local STT
4. Text is sent to n8n workflow
5. n8n queries local LLM and processes response
6. Response text returns to backend
7. Backend converts text to speech using local Coqui TTS
8. Audio response streams back to client for playback

## Getting Started

### Prerequisites

1. **Docker & Docker Compose**: [Install Docker](https://docs.docker.com/get-docker/)
2. **Node.js & npm**: Only needed for backend code modifications
3. **Python 3.7+**: For the Raspberry Pi client
4. **Arduino IDE or PlatformIO**: For the ESP32 client
5. **Git**: For repository management
6. **Local LLM Host**: Ollama or LM Studio
7. **n8n Workflow Engine**: For orchestration
8. **Speaker Reference File (Optional)**: For XTTS voice cloning, prepare a clean WAV recording of your desired voice, place in `./coqui-tts-api/speaker-wavs/` (MP3 files will be auto-converted to WAV)
9. **NVIDIA GPU with CUDA Support (Recommended)**: For optimal performance with XTTS models
10. **NVIDIA Container Toolkit**: To allow Docker containers to access GPU (required for XTTS high-quality synthesis)

### Running the Project

1.  Clone this repository:
    ```bash
    git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
    cd YOUR_REPOSITORY_NAME
    ```
    (Replace `YOUR_USERNAME/YOUR_REPOSITORY_NAME` with your actual GitHub repository details after you create it.)

2.  Prepare your environment:
   - Copy your speaker reference file(s) to `./coqui-tts-api/speaker-wavs/` directory (MP3 or WAV format)
   - Ensure Docker is running with NVIDIA container toolkit if using GPU
   - Create a `.env` file with your configuration (see `.env.example`)

3.  Start the system:
    ```bash
    # Ensure Docker Desktop is running
    # Then, use Docker Compose commands:
    docker-compose build
    docker-compose up -d # -d runs in detached mode
    ```

4.  Access the web interface:
   Open a browser and navigate to `http://localhost:8080`

5.  Troubleshooting:
   If you encounter issues, refer to the [Troubleshooting Guide](docs/troubleshooting.md)

### Configuration

Create a `.env` file in the project root directory:

```dotenv
# Backend Configuration
BACKEND_PORT=3000

# n8n Configuration
N8N_WEBHOOK_URL=YOUR_N8N_WEBHOOK_RECEIVE_TEXT_URL

# IP address of the machine running Docker
BACKEND_HOST_IP=YOUR_DOCKER_HOST_IP
```

### Installation

1. **Local Directories for Models & Data**:
   The directory structure for model storage is already set up in the repository:
   ```
   coqui-tts-api/
     ├── coqui-models-data/  # Models will be cached here
     └── speaker-wavs/       # Place voice reference WAVs here
   ```
   
   If using XTTS voice cloning:
   - Place your WAV file in `coqui-tts-api/speaker-wavs/`
   - Update `COQUI_SPEAKER_WAV` in `docker-compose.yml` to match your file's name

2. **Backend & Services** (using Docker):
   ```bash
   # In project root directory
   docker-compose up --build -d
   ```

3. **Raspberry Pi Client**:
   ```bash
   cd rpi_client
   pip install -r requirements.txt
   
   # Set backend connection (one of these methods)
   export WEBSOCKET_URL="ws://<BACKEND_HOST_IP>:<BACKEND_PORT>"
   # or
   pip install python-dotenv
   # then create .env file with WEBSOCKET_URL defined
   ```
   
   For wake word detection:
   ```bash
   pip install vosk
   ```

4. **ESP32 Client**:
   - Configure WiFi and server settings in the code
   - Upload using Arduino IDE or PlatformIO:
   ```bash
   cd esp32_client
   # See esp32_client/README.md for detailed instructions
   pio run -e esp32s3 -t upload  # For best wake word performance
   ```

### Running the System

1. Start required external services (LLM, n8n)
2. Ensure your speaker WAV file is placed in the `coqui-tts-api/speaker-wavs/` directory (for XTTS voice cloning)
3. Start Docker containers:
   ```bash
   docker-compose up --build -d
   ```
4. Monitor service logs during first run, especially for model downloads:
   ```bash
   # Monitor the TTS service logs specifically
   docker-compose logs -f coqui-tts-api
   ```

### Stopping the System

```bash
docker-compose down
```

## Client Options

### Web UI
- Easiest setup, works on any device with a browser
- Requires manual button press to activate recording
- Automatically stops recording after a period of silence (~2 seconds) or max duration (~30 seconds)
- May have browser permission issues for microphone access

### Raspberry Pi
- Good balance of features and ease of setup
- Supports wake word detection via Vosk (open source, no API key needed)
- Standardized wake word: "hey assistant"
- Automatically stops recording after a configurable period of silence (defaults to ~2 seconds)
- Suitable for permanent installations

### ESP32
- Most cost-effective and power-efficient option
- Built-in wake word detection using ESP-SR library (open source, no API key needed)
- Standardized wake word: "hey assistant" 
- Best performance on ESP32-S3 hardware
- Perfect for compact or battery-powered installations
- See `esp32_client/HARDWARE_SETUP.md` for hardware connections

## Project Structure

```
docker-compose.yml   # Docker configuration for all services
readme.md            # This file - project overview and setup
.env.example         # Example environment variables (copy to .env)
.gitignore           # Specifies intentionally untracked files for Git

backend/             # Node.js/Express backend server
  Dockerfile         # Docker configuration for backend
  package.json       # Node.js dependencies and scripts
  server.js          # Main server application code
  README.md          # Backend specific documentation

coqui-tts-api/       # Coqui TTS API service (Text-to-Speech)
  app.py             # FastAPI application for Coqui TTS
  Dockerfile         # Docker configuration for Coqui TTS service
  requirements.txt   # Python dependencies for Coqui TTS
  README.md          # Coqui TTS service-specific documentation
  prestart.py        # Script run before starting the TTS service (e.g., license handling)
  auto_license.py    # Helper script for license agreement (if used)
  convert_mp3.py     # Helper script for MP3 to WAV conversion (if used by prestart)
  patch_tts.py       # Helper script for patching TTS (if used)
  tts_wrapper.py     # Wrapper for TTS functionalities (if used)
  coqui-models-data/ # Directory for downloaded Coqui TTS model cache (mounted as volume)
    tts_models--multilingual--multi-dataset--xtts_v2/ # Example model structure
      # ...model files...
  speaker-wavs/      # Directory for XTTS speaker reference WAV/MP3 files (mounted as volume)
    Wj0v.mp3         # Example MP3 speaker file
    Wj0v.wav         # Example WAV speaker file (may be converted from MP3)
    convert_mp3_to_wav.py # Script to convert MP3s in this folder to WAV

docs/                # Additional documentation files
  coqui_tts_guide.md # Guide for Coqui TTS configuration and usage
  llm_setup_guide.md # Guide for setting up Local LLM (Ollama, LM Studio)
  n8n_workflow_setup.md # Guide for setting up the n8n workflow
  troubleshooting.md # Common issues and solutions
  coqui_license_fix.md # Details on Coqui TTS license handling

esp32_client/        # ESP32 microcontroller client
  esp32_client.ino   # Main Arduino/C++ code for the ESP32
  HARDWARE_SETUP.md  # Hardware connection guide for ESP32
  platformio.ini     # PlatformIO project configuration
  README.md          # ESP32 client specific instructions

rpi_client/          # Raspberry Pi client
  client.py          # Main Python client code for Raspberry Pi
  requirements.txt   # Python dependencies for RPi client
  README.md          # Raspberry Pi client specific instructions

web_ui/              # Web interface files (HTML, JS, CSS for browser client)
  Dockerfile         # Docker configuration for Nginx web server
  index.html         # Main HTML file for the web UI
  script.js          # JavaScript for web UI functionality
  README.md          # Web UI specific instructions and notes

whisper-api/         # Whisper STT API service (Speech-to-Text)
  app.py             # FastAPI application for Whisper STT
  Dockerfile         # Docker configuration for Whisper STT service
  requirements.txt   # Python dependencies for Whisper STT
  README.md          # (Should be created if not present) Whisper STT service-specific documentation
```

## Troubleshooting

- **Connection Issues**: Ensure your BACKEND_HOST_IP is correctly set to your Docker host's actual IP address on your network, not localhost/127.0.0.1
- **Audio Problems**: Check if your microphone and speaker are properly configured
- **Wake Word Detection Issues**: Adjust sensitivity settings in client code. All clients use "hey assistant" as the wake word.
- **Docker Problems**: Check container logs with `docker-compose logs -f`

## Future Improvements

- Add support for multiple wake words and voices
- Implement multi-room synchronization
- Add more client device options (Android, iOS apps)
- Improve offline performance with lighter models

## Further Documentation

*   [LLM Setup Guide](docs/llm_setup_guide.md)
*   [n8n Workflow Setup](docs/n8n_workflow_setup.md)
*   [Coqui TTS Guide](docs/coqui_tts_guide.md)
*   [Coqui TTS License Fix Details](docs/coqui_license_fix.md)
*   [Troubleshooting Guide](docs/troubleshooting.md)
*   Refer to individual `README.md` files within service directories (`backend/`, `coqui-tts-api/`, etc.) for more component-specific details.