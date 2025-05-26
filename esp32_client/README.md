# ESP32 Voice Assistant Client

This is the ESP32-based client for the voice assistant system. It listens for the wake word "hey assistant", then streams audio to the backend server for processing.

## Features

- Wake word detection using Espressif's esp-sr library (no API keys required)
- Audio streaming via WebSockets
- Energy-efficient design for battery operation
- Visual feedback via onboard LED
- Manual trigger button as fallback option

## Hardware Requirements

See [HARDWARE_SETUP.md](HARDWARE_SETUP.md) for detailed hardware setup instructions.

- ESP32 development board (ESP32-S3 recommended for better wake word performance)
- I2S MEMS microphone (e.g., INMP441, SPH0645)
- LED for status indication
- Push button for manual trigger

## Configuration

Edit the following in `esp32_client.ino`:

1. WiFi credentials:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```

2. Backend server address:
   ```cpp
   const char* websocket_host = "YOUR_BACKEND_HOST_IP";
   const int websocket_port = 3000;
   ```

3. Pin assignments (if different from defaults):
   ```cpp
   const int BUTTON_PIN = 12;
   const int LED_STATUS_PIN = 2;
   const int I2S_SD_PIN = 32;
   const int I2S_SCK_PIN = 14;
   const int I2S_WS_PIN = 15;
   ```

## Building and Flashing

This project uses PlatformIO for dependency management and easy build/upload. Use one of the following methods:

### Using VS Code with PlatformIO Extension

1. Open this folder in VS Code with the PlatformIO extension installed
2. Click the "Build" button or press Ctrl+Alt+B
3. Connect your ESP32 via USB
4. Click the "Upload" button or press Ctrl+Alt+U

### Using PlatformIO CLI

```bash
# Build the project
pio run

# Upload to ESP32
pio run --target upload
```