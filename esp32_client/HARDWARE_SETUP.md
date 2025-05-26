# ESP32 Client Hardware Setup

This document provides hardware connection instructions for setting up the ESP32 Voice Assistant client with I2S microphone and wake word detection.

## Required Hardware

- ESP32 development board (ESP32-DevKitC, NodeMCU-32S, etc.) 
  - ESP32-S3 recommended for better wake word performance
- I2S MEMS microphone (INMP441 or SPH0645 recommended)
- Push button for manual trigger (optional, fallback for wake word)
- LED for status indication (optional, can use built-in LED)
- Breadboard and jumper wires for connections
- 5V power supply or USB cable for power

## Wiring Connections

### I2S Microphone (INMP441 or SPH0645)

| Microphone Pin | ESP32 Pin | Description      |
|----------------|-----------|------------------|
| VDD            | 3.3V      | Power            |
| GND            | GND       | Ground           |
| SD             | GPIO 32   | Serial Data      |
| SCK (or SCL)   | GPIO 14   | Serial Clock     |
| WS (or L/R)    | GPIO 15   | Word Select      |
| L/R (if SPH)   | GND       | Left/Right select|

### Push Button (Optional)

| Button Pin | ESP32 Pin | Description       |
|------------|-----------|-------------------|
| Pin 1      | GPIO 12   | Button input      |
| Pin 2      | GND       | Ground            |

A 10K pull-up resistor is recommended between GPIO 12 and 3.3V if your button doesn't have an internal pull-up.

### Status LED (Optional)

| LED Pin    | ESP32 Pin | Description       |
|------------|-----------|-------------------|
| Anode (+)  | GPIO 2    | Through 220Ω resistor |
| Cathode (-) | GND       | Ground            |

**Note:** If you're using the built-in LED, which is typically on GPIO 2, no external LED is needed.

## Wiring Diagram

```
ESP32                INMP441/SPH0645
+-------+            +-------+
| 3.3V  |----------->| VDD   |
| GND   |----------->| GND   |
| GPIO32|<-----------| SD    |
| GPIO14|----------->| SCK   |
| GPIO15|----------->| WS    |
+-------+            +-------+

ESP32                BUTTON
+-------+            +-------+
| GPIO12|<-----------| PIN1  |
| GND   |----------->| PIN2  |
+-------+            +-------+
                       ▲
                       │
                    (PRESS)

ESP32                LED
+-------+            +---+
| GPIO2 |---[220Ω]-->|   |
| GND   |----------->|   |
+-------+            +---+
```

## Hardware Notes

1. **Microphone Selection**: INMP441 is often easier to work with than SPH0645 and provides cleaner audio.

2. **Microphone Orientation**: For wake word detection, ensure the microphone is positioned with the sound port facing outward and not obstructed.

3. **Wake Word Performance**: 
   - ESP32-S3 has better performance than original ESP32 for wake word detection
   - Place the microphone away from noise sources
   - Consider adding a simple pop filter (foam) over the microphone for improved performance

4. **ESP32 Board Selection**:
   - For wake word detection: ESP32-S3 is recommended
   - For basic recording only (button trigger): Any ESP32 model is sufficient

5. **Power Supply**:
   - Use a clean, stable power supply
   - USB power from a computer can sometimes introduce noise into the audio circuit
   - Consider using a separate power supply if you experience noise issues

## Wake Word Optimization

For optimal wake word performance:

1. **Adjust Sensitivity**: In the sketch, tune `WAKE_WORD_THRESHOLD` (default: 0.6)
   - Higher threshold (e.g., 0.8) means fewer false positives but may miss some activations
   - Lower threshold (e.g., 0.4) makes detection more sensitive but increases false positives

2. **Physical Placement**:
   - Keep the microphone at least 1 meter away from loud noise sources
   - Position the device where the wake word will be spoken toward the microphone
   - Wall-mounting often works well for consistent detection

3. **Testing Setup**:
   - Use the serial monitor to see if wake words are being detected properly
   - LEDs will flash in a specific pattern when wake word is detected
   - Experiment with speaking volume and distance for best results

## Troubleshooting Common Issues

1. **No Audio Being Captured**:
   - Verify microphone connections, especially SD, SCK, and WS pins
   - Check power is properly supplied to the microphone (3.3V)
   - Try a different I2S microphone if available

2. **Wake Word Not Detecting**:
   - Ensure you're using an ESP32-S3 for best performance
   - Decrease the detection threshold in the code
   - Check if the correct wake word is set in `WAKE_WORD_MODEL` and `WAKE_WORD_NAME`
   - Make sure you're using the latest ESP-SR library

3. **Intermittent Operation**:
   - Poor power supply can cause instability - try a different USB cable or power source
   - Add capacitors (100uF and 0.1uF) between power and ground near the ESP32
   - Reduce WiFi interference by moving the device away from routers or other RF sources

4. **WebSocket Connection Issues**:
   - Verify WiFi credentials are correct
   - Confirm the backend server is running and accessible
   - Check that the port is not blocked by firewall