import pyaudio
import websocket # pip install websocket-client (not websockets)
import time
import threading
import json
import sys
import signal
import os # Import os to access environment variables
import struct # Required for unpacking audio data
import audioop # For RMS calculation
from dotenv import load_dotenv # Optional: pip install python-dotenv

# Optional: Load .env file from the current directory if it exists
# Useful if you prefer managing the client config via a local .env
# load_dotenv()

# Import Vosk for wake word detection (open source, no API key needed)
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
    print("Vosk library found. Wake word detection is available.")
except ImportError:
    print("Vosk library not found. Install it with: pip install vosk")
    print("You will need to use manual trigger (Enter key) instead of wake word.")
    VOSK_AVAILABLE = False

# Wake word configuration
WAKE_WORD_ENABLED = True  # Set to False to disable wake word detection
WAKE_WORD = "hey assistant"    # The wake word to listen for
WAKE_WORD_SENSITIVITY = 0.5  # Not directly used by Vosk but kept for compatibility

# Path to Vosk model - download from https://alphacephei.com/vosk/models
# Use small model for wake word detection (vosk-model-small-en-us-0.15)
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"  # Set to path where you downloaded and extracted the model

# !!! CONFIGURATION (now primarily from environment variables) !!!
# The RPi Client runs OUTSIDE Docker, so it needs the HOST IP where Docker exposes the backend port.
# Set the WEBSOCKET_URL environment variable before running this script.
# Example: export WEBSOCKET_URL="ws://192.168.1.50:3000"
# Or set it in a local .env file and use load_dotenv()
DEFAULT_WEBSOCKET_URL = f"ws://{os.getenv('BACKEND_HOST_IP', 'YOUR_BACKEND_IP')}:{os.getenv('BACKEND_PORT', '3000')}"
WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', DEFAULT_WEBSOCKET_URL)

# !!! END CONFIGURATION !!!

# Audio Einstellungen (muss mit Backend und STT Engine übereinstimmen)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000 # Sample Rate
FRAMES_PER_BUFFER = 1024 # Chunk size for processing audio
SILENCE_THRESHOLD = 500  # RMS threshold for considering audio as silence (adjust as needed)
SILENCE_DURATION_SEC = 2.0 # How many seconds of silence triggers stop

class VoiceClient:
    def __init__(self, websocket_url):
        self.websocket_url = websocket_url
        self.ws = None
        self.ws_thread = None
        self.ws_connected = threading.Event()
        self.audio_interface = pyaudio.PyAudio()
        self.audio_stream_input = None
        self.audio_stream_output = None
        self.recording = False
        self.stop_event = threading.Event()
        self.last_audio_receive_time = 0
        self.last_speech_time = 0 # Track time of last non-silent audio chunk

        # --- Wake Word Engine Initialization ---
        self.wake_word_engine = None
        self.vosk_recognizer = None
        
        if WAKE_WORD_ENABLED and VOSK_AVAILABLE:
            try:
                # Check if Vosk model path exists
                if not os.path.exists(VOSK_MODEL_PATH):
                    print(f"Vosk model not found at {VOSK_MODEL_PATH}")
                    print("Please download a model from https://alphacephei.com/vosk/models")
                    print("Extract it and set VOSK_MODEL_PATH to the extracted folder")
                    print("For wake word detection, the small model is sufficient:")
                    print("https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
                    raise FileNotFoundError(f"Vosk model not found at {VOSK_MODEL_PATH}")
                
                # Initialize Vosk model
                model = Model(VOSK_MODEL_PATH)
                self.vosk_recognizer = KaldiRecognizer(model, RATE)
                
                # Set partial mode for faster response (wake word detection)
                self.vosk_recognizer.SetPartialWords(True)
                self.vosk_recognizer.SetMaxAlternatives(0)
                self.wake_word_engine = True  # Flag that we have a wake word engine
                
                print(f"Wake word engine (Vosk) initialized. Listening for wake word: '{WAKE_WORD}'")
            except Exception as e:
                print(f"Error initializing Vosk: {e}")
                print("Wake word detection disabled. Will use manual trigger.")
                self.wake_word_engine = None
        else:
            if not WAKE_WORD_ENABLED:
                print("Wake word detection disabled by configuration.")
            elif not VOSK_AVAILABLE:
                print("Vosk library not available.")
            print("!!! Press Enter to simulate wake word and start recording. !!!")
        # --- End Wake Word ---


    def _connect_websocket(self):
        """Establishes WebSocket connection in a separate thread."""
        while not self.stop_event.is_set():
            print(f"Attempting to connect to WebSocket: {self.websocket_url}")
            try:
                # Set a timeout for the connection attempt
                self.ws = websocket.create_connection(self.websocket_url, timeout=10)
                print("WebSocket connected.")
                self.ws_connected.set() # Signal that connection is established
                self._receive_loop() # Start receiving messages in this thread
            except websocket.WebSocketException as e:
                print(f"WebSocket connection/receive error: {e}")
            except Exception as e:
                print(f"Error during WebSocket connection: {e}")
            finally:
                if self.ws:
                    self.ws.close()
                self.ws = None
                self.ws_connected.clear()
                if not self.stop_event.is_set():
                    print("WebSocket disconnected. Reconnecting in 5 seconds...")
                    time.sleep(5)

    def _receive_loop(self):
        """Handles receiving messages from the WebSocket."""
        try:
            while not self.stop_event.is_set():
                message = self.ws.recv()
                self.last_audio_receive_time = time.time() # Track time for silence detection

                if isinstance(message, bytes):
                    # Play received audio data
                    self._play_audio(message)
                else:
                    # Handle JSON messages (z.B. errors, commands)
                    print(f"Received text message: {message}")
                    try:
                        msg_data = json.loads(message)
                        if msg_data.get('error'):
                            print(f"Error from server: {msg_data['error']}")
                        elif msg_data.get('event') == 'noSpeechDetected':
                            print("Server indicated no speech was detected.")
                    except json.JSONDecodeError:
                         print(f"Received non-JSON text message: {message}")
        except websocket.WebSocketConnectionClosedException:
            print("WebSocket connection closed by server.")
        except Exception as e:
            print(f"Error in receive loop: {e}")
        finally:
            print("Receive loop finished.")
            self.ws_connected.clear() # Signal disconnection


    def _play_audio(self, audio_data):
        """Plays audio data using PyAudio."""
        try:
            if self.audio_stream_output is None or not self.audio_stream_output.is_active():
                self.audio_stream_output = self.audio_interface.open(format=FORMAT,
                                                                    channels=CHANNELS,
                                                                    rate=RATE,
                                                                    output=True,
                                                                    frames_per_buffer=FRAMES_PER_BUFFER)
            self.audio_stream_output.write(audio_data)
        except Exception as e:
            print(f"Error playing audio: {e}")
            if self.audio_stream_output:
                try:
                    self.audio_stream_output.stop_stream()
                    self.audio_stream_output.close()
                except Exception as close_err:
                    print(f"Error closing output stream: {close_err}")
                finally:
                    self.audio_stream_output = None


    def _close_output_stream(self):
        """Closes the audio output stream if open."""
        if self.audio_stream_output:
            print("Closing audio output stream.")
            try:
                time.sleep(0.2)
                if self.audio_stream_output.is_active():
                    self.audio_stream_output.stop_stream()
                self.audio_stream_output.close()
            except Exception as e:
                print(f"Error closing output stream: {e}")
            finally:
                self.audio_stream_output = None

    def _listen_for_wake_word(self):
        """Listens for wake word using the microphone."""
        if self.recording: # Should not happen, but safety check
            return

        print("Starting wake word listening...")
        input_device_index = None # Use default input device
        stream = None

        try:
            # --- Wake Word Engine Logic ---
            if self.wake_word_engine and self.vosk_recognizer:
                stream = self.audio_interface.open(
                    rate=RATE,
                    channels=CHANNELS,
                    format=FORMAT,
                    input=True,
                    frames_per_buffer=FRAMES_PER_BUFFER,
                    input_device_index=input_device_index)

                print(f"Listening for wake word '{WAKE_WORD}'... (Press Ctrl+C to exit)")
                
                sys.stdout.write("🎤 ")
                sys.stdout.flush()
                
                detection_time = time.time()
                
                while not self.stop_event.is_set():
                    audio_data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                    
                    current_time = time.time()
                    if current_time - detection_time >= 5:
                        sys.stdout.write("🎤 ")
                        sys.stdout.flush()
                        detection_time = current_time
                    
                    if self.vosk_recognizer.AcceptWaveform(audio_data):
                        result = json.loads(self.vosk_recognizer.Result())
                        text = result.get("text", "").lower()
                        if WAKE_WORD.lower() in text:
                            print(f"\n✅ Wake word '{WAKE_WORD}' detected in: '{text}'")
                            stream.stop_stream()
                            stream.close()
                            self._start_recording()  # Start recording audio for command
                            return  # Exit wake word loop
                    else:
                        partial = json.loads(self.vosk_recognizer.PartialResult())
                        partial_text = partial.get("partial", "").lower()
                        if WAKE_WORD.lower() in partial_text:
                            print(f"\n✅ Wake word '{WAKE_WORD}' detected in partial: '{partial_text}'")
                            stream.stop_stream()
                            stream.close()
                            self._start_recording()  # Start recording audio for command
                            return  # Exit wake word loop
            else:
                print("--- Press Enter to simulate wake word ---")
                enter_pressed = threading.Event()
                def wait_for_enter():
                    input() # Blocks here until Enter is pressed
                    enter_pressed.set()

                input_thread = threading.Thread(target=wait_for_enter)
                input_thread.daemon = True
                input_thread.start()

                while not self.stop_event.is_set() and not enter_pressed.is_set():
                    time.sleep(0.1)

                if enter_pressed.is_set():
                    print("--- Enter pressed (Simulated Wake Word) ---")
                    self._start_recording()
                    return

        except KeyboardInterrupt:
            print("\nKeyboard interrupt during wake word listening.")
            self.stop_event.set()
        except Exception as e:
             print(f"Error during wake word listening: {e}")
             time.sleep(1)
        finally:
            if stream and stream.is_active():
                stream.stop_stream()
                stream.close()
            print("Wake word listening stopped.")


    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for PyAudio stream. Sends audio data via WebSocket and checks for silence."""
        is_silent = False
        try:
            # Calculate RMS of the current chunk
            rms = audioop.rms(in_data, self.audio_interface.get_sample_size(FORMAT))
            if rms < SILENCE_THRESHOLD:
                is_silent = True
            else:
                self.last_speech_time = time.time() # Update time of last speech detected

        except Exception as rms_err:
            print(f"Error calculating RMS: {rms_err}")

        if self.recording and self.ws_connected.is_set():
            try:
                self.ws.send(in_data, websocket.ABNF.OPCODE_BINARY)
            except websocket.WebSocketException as e:
                print(f"Error sending audio chunk via WebSocket: {e}")
            except Exception as e:
                print(f"Unexpected error in audio callback: {e}")

        # Check for silence duration outside the WebSocket send block
        if self.recording and is_silent:
            if time.time() - self.last_speech_time > SILENCE_DURATION_SEC:
                print(f"\nSilence detected for > {SILENCE_DURATION_SEC} seconds.")
                self.recording = False # Signal the recording loop to stop
                print("Signaling recording loop to stop due to silence.")

        return (in_data, pyaudio.paContinue)


    def _start_recording(self):
        """Starts recording audio and streaming it to the backend."""
        if self.recording:
            return
        if not self.ws_connected.is_set():
            print("Cannot start recording: WebSocket not connected.")
            return

        self.recording = True
        self.last_speech_time = time.time() # Initialize last speech time
        print("Recording started...")
        self._close_output_stream()

        try:
            self.audio_stream_input = self.audio_interface.open(format=FORMAT,
                                                                 channels=CHANNELS,
                                                                 rate=RATE,
                                                                 input=True,
                                                                 frames_per_buffer=FRAMES_PER_BUFFER,
                                                                 stream_callback=self._audio_callback)
            self.audio_stream_input.start_stream()

            recording_start_time = time.time()
            max_recording_duration = 30 # Keep max duration as a fallback

            print("Recording... (Speak your command, will stop after silence)")
            sys.stdout.write("⏺ ")
            sys.stdout.flush()

            recording_indicator_time = time.time()

            while self.recording and not self.stop_event.is_set():
                current_time = time.time()

                if current_time - recording_indicator_time >= 0.5:
                    sys.stdout.write("⏺ ")
                    sys.stdout.flush()
                    recording_indicator_time = current_time

                if current_time - recording_start_time > max_recording_duration:
                    print(f"\nMax recording duration ({max_recording_duration}s) reached.")
                    self.recording = False # Ensure stop if max duration hit
                    break

                time.sleep(0.1)

        except Exception as e:
            print(f"Error starting recording stream: {e}")
            self.recording = False
        finally:
            if self.recording:
                 self._stop_recording()
            else:
                 self._stop_recording_internal()


    def _stop_recording_internal(self):
        """Internal part of stopping recording, mainly closing the stream."""
        print("\nStopping recording stream internally...")
        if self.audio_stream_input:
            try:
                if self.audio_stream_input.is_active():
                    self.audio_stream_input.stop_stream()
                self.audio_stream_input.close()
                print("Input stream closed.")
            except Exception as e:
                print(f"Error closing input stream: {e}")
            finally:
                self.audio_stream_input = None


    def _stop_recording(self):
        """Stops the audio recording stream and sends end event."""
        if not self.recording:
             self._stop_recording_internal()
             return

        self.recording = False
        print("\nStopping recording manually...")

        self._stop_recording_internal()

        if self.ws_connected.is_set():
             try:
                 print("Sending audioEnd event to server.")
                 self.ws.send(json.dumps({'event': 'audioEnd'}))
             except websocket.WebSocketException as e:
                 print(f"Failed to send audioEnd event: {e}")
             except Exception as e:
                 print(f"Error sending audioEnd event: {e}")

        print("Recording stopped. Waiting for response...")
        print("Returning to wake word listening after response.")
        self.last_audio_receive_time = 0


    def run(self):
        """Main loop: Connects WebSocket and alternates between listening and recording."""
        print("Starting Voice Client...")
        print(f"Target WebSocket: {self.websocket_url}")
        if "YOUR_BACKEND_IP" in self.websocket_url:
             print("---")
             print("WARNING: WEBSOCKET_URL seems to contain the placeholder 'YOUR_BACKEND_IP'.")
             print("Please set the WEBSOCKET_URL environment variable to the correct IP address")
             print("of the machine running the backend Docker container and the correct port.")
             print("Example: export WEBSOCKET_URL=\"ws://192.168.1.50:3000\"")
             print("---")

        self.ws_thread = threading.Thread(target=self._connect_websocket, daemon=True)
        self.ws_thread.start()

        while not self.stop_event.is_set():
            if self.ws_connected.wait(timeout=1):
                if not self.recording:
                    self._listen_for_wake_word()
                else:
                    time.sleep(0.5)
            else:
                print("Waiting for WebSocket connection...")
                time.sleep(2)

        print("Stop event received. Shutting down.")
        self._shutdown()


    def _shutdown(self):
        """Cleans up resources."""
        print("Shutting down client...")
        self.stop_event.set()

        self.vosk_recognizer = None
        print("Wake word engine resources released.")

        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                print(f"Error closing WebSocket: {e}")
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)
            if self.ws_thread.is_alive():
                print("Warning: WebSocket thread did not terminate gracefully.")

        if self.audio_stream_input and self.audio_stream_input.is_active():
            self.audio_stream_input.stop_stream()
        if self.audio_stream_input:
            self.audio_stream_input.close()
        self._close_output_stream()

        self.audio_interface.terminate()
        print("PyAudio terminated.")
        print("Client shutdown complete.")

# Graceful shutdown handler
def signal_handler(sig, frame):
    print(f"Signal {sig} received. Initiating shutdown...")
    if client:
        client.stop_event.set()

if __name__ == "__main__":
    client = None
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        client = VoiceClient(WEBSOCKET_URL)
        client.run()

    except Exception as main_err:
        print(f"An unexpected error occurred in the main execution: {main_err}")
    finally:
        if client and not client.stop_event.is_set():
            print("Main loop exited unexpectedly. Forcing shutdown.")
            client._shutdown()
        elif not client:
             print("Client initialization failed.")

    print("Program finished.")
