/*
 * ESP32 Voice Assistant Client with Wake Word Detection
 * 
 * This sketch allows an ESP32 with an I2S microphone to capture audio,
 * detect a wake word using Espressif's open-source esp-sr library (WakeNet),
 * and stream audio via WebSockets to the voice assistant backend when activated.
 * 
 * Hardware requirements:
 * - ESP32 development board (ESP32S3 recommended for better wake word performance)
 * - I2S MEMS microphone (e.g., INMP441, SPH0645)
 * - LED for status indication (optional)
 * - Push button for manual trigger (optional, fallback)
 * 
 * Dependencies:
 * - WiFi.h (Arduino ESP32 core)
 * - WebSocketsClient.h (WebSockets by Markus Sattler)
 * - I2S.h (ESP32 core)
 * - esp_wn_iface.h and esp_wn_models.h (esp-sr library for wake word detection)
 *   Note: esp-sr is an open-source library from Espressif that doesn't require API keys
 * 
 * This sketch uses Espressif's open-source WakeNet models which are freely available
 * without requiring any API keys or tokens.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiMulti.h>
#include <WebSocketsClient.h>
#include <driver/i2s.h>

// esp-sr library for wake word detection (open source, no API keys required)
// Note: Works best on ESP32-S3 for most wake words
#include "esp_wn_iface.h"
#include "esp_wn_models.h"
#include "esp_mn_models.h"

// --- CONFIGURATION (Change these values) ---
// WiFi settings
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// WebSocket server settings (replace with your backend IP and port)
const char* websocket_host = "YOUR_BACKEND_HOST_IP";
const int websocket_port = 3000;
const char* websocket_url = "/";  // Root path for WebSocket

// Wake word configuration - STANDARDIZED across all clients as "hey assistant"
// We use WAKENET_MODEL_HEY_SIRI as the underlying model since it's the closest match
// to our standardized wake word "hey assistant" available in the ESP32 library
#define WAKE_WORD_MODEL WAKENET_MODEL_HEY_SIRI
#define WAKE_WORD_CHANNELS 1          // Mono microphone
#define WAKE_WORD_NAME "hey assistant" // Our standardized wake word
#define WAKE_WORD_THRESHOLD 0.6       // Detection threshold (higher = fewer false positives)

// Hardware pins
const int BUTTON_PIN = 12;            // GPIO pin for manual wake button (optional)
const int LED_STATUS_PIN = 2;         // Built-in LED (usually GPIO2 on most dev boards)
const int I2S_SD_PIN = 32;            // I2S microphone SD (data) pin
const int I2S_SCK_PIN = 14;           // I2S microphone SCK (clock) pin
const int I2S_WS_PIN = 15;            // I2S microphone WS (word select) pin

// Audio settings
const int SAMPLE_RATE = 16000;        // Match your backend's expected sample rate
const int SAMPLE_BITS = 16;           // 16-bit audio
const int NUM_CHANNELS = 1;           // Mono
const int I2S_PORT = I2S_NUM_0;       // I2S peripheral to use (0 or 1)
// Buffer size should be a multiple of sample size
const int BUFFER_SIZE = 512;          // Buffer size for audio data (in bytes)

// --- VARIABLES ---
WiFiMulti WiFiMulti;
WebSocketsClient webSocket;
bool isRecording = false;
bool isConnected = false;
unsigned long recordingStartTime = 0;
const unsigned long MAX_RECORDING_MS = 10000;  // Max recording time (10 seconds)
bool buttonPressed = false;
bool buttonState = false;
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;  // Debounce time in milliseconds

// Wake word detection variables
static const esp_wn_iface_t *wake_word_model;
static esp_wn_iface_t *model_handle = NULL;
static int audio_chunksize = 0;
static int16_t *audio_buffer = NULL;
const int channels = WAKE_WORD_CHANNELS; 
bool wake_word_enabled = true;

// --- I2S AUDIO SETUP FUNCTION ---
bool setupI2S() {
  // I2S configuration
  static const i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = (i2s_bits_per_sample_t)SAMPLE_BITS,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,  // For mono microphone
    .communication_format = I2S_COMM_FORMAT_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = BUFFER_SIZE / 2,  // in terms of sample frames, not bytes
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  // I2S pin configuration
  static const i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK_PIN,    // SCK
    .ws_io_num = I2S_WS_PIN,      // WS
    .data_out_num = I2S_PIN_NO_CHANGE,  // Not used for input
    .data_in_num = I2S_SD_PIN     // SD (microphone data)
  };

  // Install and start I2S driver
  esp_err_t err = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  if (err != ESP_OK) {
    Serial.printf("Failed to install I2S driver: %d\n", err);
    return false;
  }

  err = i2s_set_pin(I2S_PORT, &pin_config);
  if (err != ESP_OK) {
    Serial.printf("Failed to set I2S pins: %d\n", err);
    return false;
  }

  return true;
}

// --- WAKE WORD SETUP FUNCTION ---
bool setupWakeWord() {
  // Get wake word model
  wake_word_model = esp_wn_handle_from_model_id(WAKE_WORD_MODEL);
  
  if (!wake_word_model) {
    Serial.println("Wake word model initialization failed");
    return false;
  }
  
  // Create model instance
  model_handle = wake_word_model->create(WAKE_WORD_THRESHOLD);
  if (!model_handle) {
    Serial.println("Failed to create wake word model instance");
    return false;
  }
  
  // Get audio buffer chunk size (typically 30ms for WakeNet)
  audio_chunksize = wake_word_model->get_samp_chunksize(model_handle);
  Serial.printf("Wake word model initialized. Chunk size: %d samples\n", audio_chunksize);
  
  // Allocate audio buffer for wake word processing
  audio_buffer = (int16_t *)malloc(audio_chunksize * sizeof(int16_t));
  if (!audio_buffer) {
    Serial.println("Failed to allocate audio buffer");
    wake_word_model->destroy(model_handle);
    return false;
  }
  
  Serial.printf("Wake word detector initialized. Listening for '%s'\n", WAKE_WORD_NAME);
  return true;
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("[WebSocket] Disconnected");
      isConnected = false;
      break;
      
    case WStype_CONNECTED:
      Serial.println("[WebSocket] Connected");
      isConnected = true;
      // Flash LED to indicate successful connection
      for (int i = 0; i < 3; i++) {
        digitalWrite(LED_STATUS_PIN, HIGH);
        delay(100);
        digitalWrite(LED_STATUS_PIN, LOW);
        delay(100);
      }
      break;
      
    case WStype_TEXT:
      // Handle text messages
      Serial.println("[WebSocket] Received text message");
      // Could handle control messages from server
      break;
      
    case WStype_BIN:
      // Received binary data (likely audio for playback, not implemented here)
      Serial.printf("[WebSocket] Received binary data (%u bytes)\n", length);
      break;
      
    case WStype_ERROR:
      Serial.println("[WebSocket] Error");
      break;
      
    default:
      break;
  }
}

void startRecording() {
  if (!isRecording && isConnected) {
    Serial.println("Starting recording...");
    isRecording = true;
    recordingStartTime = millis();
    digitalWrite(LED_STATUS_PIN, HIGH);  // Turn on LED while recording
    wake_word_enabled = false;          // Disable wake word detection while recording
  }
}

void stopRecording() {
  if (isRecording) {
    Serial.println("Stopping recording...");
    isRecording = false;
    digitalWrite(LED_STATUS_PIN, LOW);  // Turn off LED
    // Send an 'end-of-audio' signal to the server if needed
    if (isConnected) {
      String endMsg = "{\"event\":\"audioEnd\"}";
      webSocket.sendTXT(endMsg);
    }
    wake_word_enabled = true;          // Re-enable wake word detection
  }
}

void checkButton() {
  // Read the button state
  bool reading = digitalRead(BUTTON_PIN) == LOW;  // Assuming active LOW (button connects to GND when pressed)
  
  // Check for button state change with debouncing
  if (reading != buttonState) {
    lastDebounceTime = millis();
  }
  
  if ((millis() - lastDebounceTime) > debounceDelay) {
    // If the button state has changed and is stable
    if (reading != buttonPressed) {
      buttonPressed = reading;
      
      // Button was just pressed
      if (buttonPressed) {
        if (!isRecording) {
          startRecording();
        } else {
          stopRecording();
        }
      }
    }
  }
  
  buttonState = reading;
}

// --- WAKE WORD DETECTION FUNCTION ---
bool detectWakeWord() {
  size_t bytes_read = 0;
  
  // Check if wake word detection is enabled
  if (!wake_word_enabled || !model_handle || !audio_buffer) {
    return false;
  }
  
  // Read audio chunk for wake word processing
  esp_err_t result = i2s_read(I2S_PORT, audio_buffer, audio_chunksize * sizeof(int16_t), &bytes_read, 0);
  
  if (result != ESP_OK || bytes_read <= 0) {
    return false;
  }
  
  // Process audio for wake word detection
  int wake_word_detected = wake_word_model->detect(model_handle, audio_buffer);
  
  if (wake_word_detected) {
    Serial.printf("Wake word '%s' detected!\n", WAKE_WORD_NAME);
    
    // Triple LED flash to indicate wake word detected
    for (int i = 0; i < 3; i++) {
      digitalWrite(LED_STATUS_PIN, HIGH);
      delay(50);
      digitalWrite(LED_STATUS_PIN, LOW);
      delay(50);
    }
    
    return true;
  }
  
  return false;
}

void processAudio() {
  if (isRecording && isConnected) {
    // Check if maximum recording time is exceeded
    if (millis() - recordingStartTime > MAX_RECORDING_MS) {
      Serial.println("Maximum recording time reached.");
      stopRecording();
      return;
    }
    
    // Read audio data from I2S
    int16_t audio_buffer[BUFFER_SIZE / 2]; // Buffer for 16-bit samples
    size_t bytes_read = 0;
    
    // Read from I2S
    esp_err_t result = i2s_read(I2S_PORT, audio_buffer, BUFFER_SIZE, &bytes_read, 0);
    
    if (result == ESP_OK && bytes_read > 0) {
      // Send the audio data via WebSocket
      webSocket.sendBIN((uint8_t*)audio_buffer, bytes_read);
    }
  }
}

void setup() {
  // Initialize serial for debugging
  Serial.begin(115200);
  delay(10);
  Serial.println("\n\nESP32 Voice Assistant Client with Wake Word Detection");
  
  // Initialize GPIO
  pinMode(BUTTON_PIN, INPUT_PULLUP);  // Button with internal pull-up
  pinMode(LED_STATUS_PIN, OUTPUT);
  digitalWrite(LED_STATUS_PIN, LOW);
  
  // Connect to WiFi
  WiFiMulti.addAP(ssid, password);
  Serial.println("Connecting to WiFi...");
  
  // Flash LED while connecting
  while (WiFiMulti.run() != WL_CONNECTED) {
    digitalWrite(LED_STATUS_PIN, HIGH);
    delay(100);
    digitalWrite(LED_STATUS_PIN, LOW);
    delay(400);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  
  // Setup I2S audio input
  if (setupI2S()) {
    Serial.println("I2S initialized successfully");
  } else {
    Serial.println("Failed to initialize I2S!");
    blinkErrorLed();
  }

  // Setup wake word detection
  if (setupWakeWord()) {
    Serial.println("Wake word detector initialized");
  } else {
    Serial.println("Failed to initialize wake word detector!");
    Serial.println("Continuing without wake word (using button only)");
    wake_word_enabled = false;
  }
  
  // Setup WebSocket connection
  Serial.printf("Connecting to WebSocket server: %s:%d\n", websocket_host, websocket_port);
  webSocket.begin(websocket_host, websocket_port, websocket_url);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);  // Try to reconnect every 5 seconds if connection is lost
  
  // Signal setup complete
  for (int i = 0; i < 5; i++) {
    digitalWrite(LED_STATUS_PIN, HIGH);
    delay(50);
    digitalWrite(LED_STATUS_PIN, LOW);
    delay(50);
  }
  
  if (wake_word_enabled) {
    Serial.printf("Setup complete. Say '%s' or press the button to start recording.\n", WAKE_WORD_NAME);
  } else {
    Serial.println("Setup complete. Press the button to start recording.");
  }
}

// Simple error indicator with rapid LED blinking
void blinkErrorLed() {
  while (true) {
    digitalWrite(LED_STATUS_PIN, HIGH);
    delay(50);
    digitalWrite(LED_STATUS_PIN, LOW);
    delay(50);
  }
}

void loop() {
  // Handle WebSocket events
  webSocket.loop();
  
  // Check button state
  checkButton();
  
  // If we're not recording, check for wake word
  if (!isRecording && wake_word_enabled) {
    if (detectWakeWord()) {
      startRecording();
    }
  }
  
  // Process and send audio if recording
  if (isRecording) {
    processAudio();
  }
  
  // Small delay to avoid consuming too much CPU if not doing either task
  if (!isRecording && !wake_word_enabled) {
    delay(10);
  }
}