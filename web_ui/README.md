# Web UI for Voice Assistant

This is the web-based interface for the voice assistant. It provides a simple user interface to:

1. Record audio via the microphone
2. Send the audio to the backend for processing
3. Play back the TTS response

## Important: Backend URL Configuration

The web interface needs to connect to the backend service via WebSocket. Since the web page runs in your browser (outside the Docker network), it needs to use the actual IP address or hostname of the machine running the Docker containers.

### Configuration Options

1. **Local Testing (same machine):**
   - Using `localhost` works if you're accessing the web UI from the same machine
   - The script.js currently uses: `ws://localhost:3000`

2. **Accessing from other devices (phones, tablets, other computers):**
   - You need to update the backend URL to use your machine's IP address
   - Run the provided helper script: `update_backend_url.cmd`
   - Optionally specify an IP: `update_backend_url.cmd 192.168.1.x` (replace with your actual IP)
   - Rebuild the web-ui container: `docker-compose up -d --build web-ui`

### Common Issues

If you see the error "Backend URL is not configured correctly" or if the web UI can't connect to the backend:

1. Check that the backend service is running (`docker-compose ps`)
2. Make sure the IP address in `script.js` is correct and accessible from your device
3. Verify that port 3000 is exposed and not blocked by a firewall

## Development

If you need to make changes to the web UI:

1. Edit the HTML, CSS, or JavaScript files
2. Rebuild the container: `docker-compose up -d --build web-ui`

For faster development, you can mount the web_ui directory as a volume in docker-compose.yml to avoid rebuilding the container for each change.
