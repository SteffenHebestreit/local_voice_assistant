# Voice Assistant Troubleshooting Guide

*Last updated: May 27, 2025*

## Common Issues

### TTS Voice Issues

1. **XTTS License Agreement Issue**
   - If you see an error about accepting the XTTS model license agreement
   - The system now uses the `COQUI_TOS_AGREED=1` environment variable in the Dockerfile to automatically accept the license
   - If you still encounter issues, run the `accept_license.cmd` script which will automatically accept the license
   - Then run `rebuild_coqui.cmd` to rebuild and restart the Coqui TTS container
   - The license agreement will be automatically accepted during container startup

2. **MP3 to WAV Conversion**
   - The system now automatically converts MP3 reference files to WAV format at startup
   - You can manually convert files using the `convert_mp3_to_wav.py` script in the `coqui-tts-api/speaker-wavs` directory
   - The `Wj0v.wav` file should be available for voice cloning

2. **XTTS Voice Not Working**
   - Ensure the `COQUI_SPEAKER_WAV` environment variable in `docker-compose.yml` points to a valid WAV file
   - The path should be `/app/speaker_files/Wj0v.wav` or another valid WAV file
   - Check if the file exists inside the container with `docker exec -it coqui-tts-api ls -la /app/speaker_files`

3. **GPU Acceleration Issues**
   - Verify NVIDIA drivers are installed with `nvidia-smi`
   - Check that nvidia-docker2 is installed
   - The `USE_CUDA` environment variable in `docker-compose.yml` should be set to `true`

### STT Issues

1. **Whisper Not Recognizing Speech**
   - Check if the `whisper-models` volume is properly mounted
   - Verify the model is downloaded (container should download it automatically)
   - Check logs for any errors with `docker logs whisper-api`

2. **404 Error with Whisper API**
   - If you see a 404 error from the STT API, ensure the endpoint URLs match
   - In `.env`, set `WHISPER_API_URL=http://whisper-api:9000/transcribe`
   - The API accepts the audio file with the field name `file`
   - Run `rebuild_whisper.cmd` to apply the changes

3. **"No audio file provided" Error**
   - If you see a 400 error with "No audio file provided", there's an issue with FormData
   - Run the `install_form_data.cmd` script to install the required Node.js package
   - Then run `rebuild_backend.cmd` to rebuild the backend container
   - This fixes issues with FormData compatibility in Node.js

### Backend Issues

1. **n8n Connection Problems**
   - If you see errors like "ECONNRESET" or "TLS connection was established"
   - The backend is unable to connect to your n8n webhook URL
   - Verify the `N8N_WEBHOOK_URL` environment variable is correct
   - Check that n8n is running and accessible
   - The backend now includes a fallback response mechanism that will still respond to the user
   - You can also try using HTTP instead of HTTPS for local testing

2. **"ENOTFOUND" Error with Coqui TTS API**
   - If you see "getaddrinfo ENOTFOUND coqui-tts-api" error in the logs
   - The Docker network is not properly configured
   - Make sure the coqui-tts-api service has the `networks: [voiceapp-network]` property in docker-compose.yml
   - Run `rebuild_all.cmd` to rebuild all services and ensure they're on the same network

3. **Web UI Backend URL Issue**
   - If you see "Backend URL is not configured correctly" error in the Web UI
   - Run the `update_backend_url.cmd` script to set the correct IP address
   - For accessing from other devices on your network, use your machine's IP address
   - Command: `update_backend_url.cmd 192.168.1.x` (replace with your actual IP)
   - Then rebuild the web-ui container: `docker-compose up -d --build web-ui`

## Quick Commands

- **Start the entire stack**: `docker-compose up`
- **Rebuild containers**: `docker-compose build`
- **View logs**: `docker-compose logs -f [service_name]`
- **Enter a container**: `docker exec -it [container_name] bash`
- **Stop all containers**: `docker-compose down`

## Model Management

- XTTS models are stored in: `./coqui-tts-api/coqui-models-data`
- Speaker reference files are in: `./coqui-tts-api/speaker-wavs`
- Whisper models are stored in a Docker volume named `whisper-models`
