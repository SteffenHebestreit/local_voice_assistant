// --- UI Elements ---
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const statusDiv = document.getElementById('status');
const transcriptDiv = document.getElementById('transcript');
const responseDiv = document.getElementById('response');

// --- Configuration ---
// !!! IMPORTANT: This URL needs the IP address of the machine HOSTING the Docker containers !!!
// It cannot use 'localhost' or a Docker service name because this script runs in the user's browser,
// outside the Docker network. The port should be the one mapped in docker-compose.yml for the backend.
// Get the host IP from the .env file or system settings and configure it here.
// Example: const backendUrl = 'ws://10.10.1.106:3000';
const backendUrl = 'ws://localhost:3000'; // Default to localhost. Change to your Docker host IP if accessing from other devices.
const MAX_RECORDING_DURATION_MS = 30000; // Auto-stop recording after 30 seconds
const SILENCE_THRESHOLD = 0.01; // RMS threshold (0-1 range, adjust based on testing)
const SILENCE_DURATION_MS = 2000; // Stop after 2 seconds of silence
const AUDIO_PROCESS_BUFFER_SIZE = 4096; // Size for ScriptProcessorNode

// --- State Variables ---
let websocket;
let mediaRecorder;
let audioContext; // For Web Audio API playback AND analysis
let analyserNode; // For silence detection
let scriptProcessorNode; // For silence detection
let sourceNode; // For silence detection input
let audioQueue = []; // Buffer for decoded audio chunks ready for playback
let playbackSourceNode; // The currently playing audio source (renamed from sourceNode)
let isPlaying = false;
let isRecording = false;
let streamBeingCaptured; // Keep track of the media stream
let recordingTimeoutId = null; // To store the max duration timeout ID
let lastSpeechTime = 0; // Track time of last speech detected

// --- Event Listeners ---
startButton.addEventListener('click', startRecording);
stopButton.addEventListener('click', stopRecording);

// --- Core Functions ---

function updateStatus(message, isError = false) {
    console.log(`Status: ${message}`);
    statusDiv.textContent = message;
    statusDiv.style.color = isError ? 'red' : 'black';
}

function connectWebSocket() {
    return new Promise((resolve, reject) => {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            resolve(websocket);
            return;
        }

        updateStatus('Connecting to backend...');
        websocket = new WebSocket(backendUrl);

        websocket.onopen = () => {
            console.log('WebSocket connected');
            updateStatus('Connected. Ready to record.');
            resolve(websocket);
        };        websocket.onmessage = (event) => {
            // Handle incoming messages (primarily audio data)
            if (event.data instanceof Blob) {
                // Received complete audio file - play it directly
                console.log(`Received complete audio blob size: ${event.data.size}`);
                playStreamingAudio(event.data);
            } else {
                // Handle text messages (e.g., errors, status updates from backend)
                console.log('Received text message:', event.data);
                try {
                    const msgData = JSON.parse(event.data);
                    if (msgData.error) {
                        updateStatus(`Server Error: ${msgData.error}`, true);
                    } else if (msgData.event === 'noSpeechDetected') {
                         updateStatus('No speech detected by server.');
                         responseDiv.textContent = '(No speech detected)';
                    } else if (msgData.type === 'directResponse') {
                        // Handle direct response message (from fallback)
                        updateStatus('Received response from server.');
                        responseDiv.textContent = msgData.text;
                    } else if (msgData.type === 'textResponse') {
                        // Text-only response when TTS fails
                        updateStatus('Received text response (TTS failed).');
                        responseDiv.textContent = msgData.text;
                    } else if (msgData.event === 'audioEnd') {
                        // Audio stream complete signal (for reference, audio already processed)
                        console.log('Audio stream complete signal received');
                    }
                    // Handle other potential text messages
                } catch (e) {
                    console.warn('Received non-JSON text message:', event.data);
                }
            }
        };

        websocket.onerror = (error) => {
            console.error('WebSocket Error:', error);
            updateStatus('WebSocket connection error!', true);
            reject(error);
            cleanupWebSocket();
            resetUI();
        };

        websocket.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            if (!isRecording) { // Don't show "closed" if user initiated stop
                 updateStatus('WebSocket connection closed.');
            }
            reject(new Error(`WebSocket closed: ${event.code} ${event.reason}`));
            cleanupWebSocket();
            resetUI();
        };
    });
}

async function startRecording() {
    if (isRecording) return;

    // Basic check for placeholder URL
    if (backendUrl.includes("YOUR_DOCKER_HOST_IP")) {
        updateStatus("Error: Backend URL is not configured correctly in script.js! Needs Docker host IP.", true);
        return;
    }

    startButton.disabled = true;
    stopButton.disabled = false;
    isRecording = true;    transcriptDiv.textContent = '...';
    responseDiv.textContent = '...';
    audioQueue = []; // Clear previous audio queue
    clearTimeout(recordingTimeoutId); // Clear any previous max duration timeout
    lastSpeechTime = Date.now(); // Initialize last speech time

    try {
        await connectWebSocket(); // Ensure WebSocket is connected

        updateStatus('Requesting microphone access...');
        streamBeingCaptured = await navigator.mediaDevices.getUserMedia({ audio: true });

        updateStatus('Microphone access granted. Setting up audio processing...');

        // --- Setup for Silence Detection --- 
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyserNode = audioContext.createAnalyser();
        analyserNode.fftSize = 2048;
        const bufferLength = analyserNode.frequencyBinCount;
        const dataArray = new Float32Array(bufferLength); // Use Float32Array for getFloatTimeDomainData

        // Use createScriptProcessor (deprecated but simpler for this example)
        // For production, consider migrating to AudioWorklet
        scriptProcessorNode = audioContext.createScriptProcessor(AUDIO_PROCESS_BUFFER_SIZE, 1, 1);

        scriptProcessorNode.onaudioprocess = (audioProcessingEvent) => {
            if (!isRecording) return;

            // Get audio data for analysis
            analyserNode.getFloatTimeDomainData(dataArray);

            // Calculate RMS
            let sum = 0.0;
            for (let i = 0; i < dataArray.length; i++) {
                sum += dataArray[i] * dataArray[i];
            }
            let rms = Math.sqrt(sum / dataArray.length);

            // console.log("RMS:", rms); // Uncomment for debugging threshold

            const currentTime = Date.now();
            if (rms > SILENCE_THRESHOLD) {
                lastSpeechTime = currentTime; // Update time if speech detected
            } else {
                // Check if silence duration exceeded
                if (currentTime - lastSpeechTime > SILENCE_DURATION_MS) {
                    console.log(`Silence detected for > ${SILENCE_DURATION_MS / 1000}s. Stopping recording.`);
                    updateStatus('Silence detected. Stopping recording.');
                    // Ensure stopRecording is called only once
                    if (isRecording) {
                         stopRecording();
                    }
                }
            }
        };

        // Connect the nodes for analysis
        sourceNode = audioContext.createMediaStreamSource(streamBeingCaptured);
        sourceNode.connect(analyserNode);
        analyserNode.connect(scriptProcessorNode);
        scriptProcessorNode.connect(audioContext.destination); // Necessary for onaudioprocess to fire
        // --- End Setup for Silence Detection ---

        updateStatus('Recording...');
        // Create MediaRecorder using the SAME stream
        mediaRecorder = new MediaRecorder(streamBeingCaptured, {
             mimeType: 'audio/webm;codecs=opus'
        });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            console.log('MediaRecorder stopped.');
            // Stop the tracks on the stream to release the microphone
            // Moved cleanup to stopRecording function
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                 console.log("Recording stopped, waiting for response...");
                 updateStatus("Processing request...");
                 // Send audioEnd event if backend expects it
                 websocket.send(JSON.stringify({ event: 'audioEnd' }));
            } else {
                 updateStatus("Recording stopped. Connection closed.");
            }
        };

        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder Error:', event.error);
            updateStatus(`MediaRecorder Error: ${event.error.name}`, true);
            stopRecording(); // Attempt to clean up
        };

        // Start recording
        mediaRecorder.start(500); // Send chunks every 500ms

        // Set the MAX duration timeout as a fallback
        recordingTimeoutId = setTimeout(() => {
            console.log(`Max recording duration (${MAX_RECORDING_DURATION_MS / 1000}s) reached.`);
            updateStatus(`Max recording duration reached. Stopping.`);
            if (isRecording && mediaRecorder?.state === 'recording') {
                stopRecording();
            }
        }, MAX_RECORDING_DURATION_MS);

    } catch (err) {
        console.error('Error starting recording:', err);
        // Handle errors
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            updateStatus('Microphone access denied.', true);
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
             updateStatus('No microphone found.', true);
        } else {
            updateStatus(`Error: ${err.message}`, true);
        }
        clearTimeout(recordingTimeoutId); // Clear max duration timeout on error
        stopRecording(); // Clean up UI and state
    }
}

function stopRecording() {
    clearTimeout(recordingTimeoutId); // Clear the max duration timeout

    if (!isRecording && mediaRecorder?.state !== 'recording') {
        resetUI();
        return;
    }

    isRecording = false; // Set flag immediately

    // --- Cleanup Audio Processing Nodes ---
    if (scriptProcessorNode) {
        scriptProcessorNode.disconnect();
        scriptProcessorNode.onaudioprocess = null; // Remove listener
        scriptProcessorNode = null;
    }
    if (analyserNode) {
        analyserNode.disconnect();
        analyserNode = null;
    }
    if (sourceNode) {
        sourceNode.disconnect();
        sourceNode = null;
    }
    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close().then(() => console.log('AudioContext closed.'));
        audioContext = null;
    }
    // --- End Cleanup ---

    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop(); // This triggers the onstop event
    } else {
         // If mediaRecorder failed or already stopped, ensure stream tracks are stopped
         if (streamBeingCaptured) {
             streamBeingCaptured.getTracks().forEach(track => track.stop());
             streamBeingCaptured = null;
         }
         resetUI();
    }

    // Stop tracks AFTER MediaRecorder has stopped if it was running
    if (streamBeingCaptured) {
        streamBeingCaptured.getTracks().forEach(track => track.stop());
        streamBeingCaptured = null;
        console.log("MediaStream tracks stopped.");
    }

    resetUI(); // Ensure UI is reset
}

function cleanupWebSocket() {
    if (websocket) {
        websocket.onopen = websocket.onmessage = websocket.onerror = websocket.onclose = null;
        if (websocket.readyState === WebSocket.OPEN || websocket.readyState === WebSocket.CONNECTING) {
            websocket.close();
        }
        websocket = null;
        console.log('WebSocket cleaned up.');
    }
}

function resetUI() {
    startButton.disabled = false;
    stopButton.disabled = true;
    isRecording = false;
    if (!statusDiv.textContent.toLowerCase().includes('error')) {
       // updateStatus('Ready.'); // Keep error messages visible
    }
}

// --- Audio Processing Functions ---

// --- Web Audio API Playback ---

function getAudioContext() {
    if (!audioContext || audioContext.state === 'closed') {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        console.log('AudioContext created/resumed.');
    }
    // Ensure context is running (required after user interaction)
    if (audioContext.state === 'suspended') {
        audioContext.resume();
    }
    return audioContext;
}

async function playStreamingAudio(audioBlob) {
    const context = getAudioContext();
    if (!context) {
        console.error("Web Audio API not supported or context couldn't be created.");
        updateStatus("Cannot play audio: Web Audio API not available.", true);
        return;
    }

    try {
        const arrayBuffer = await audioBlob.arrayBuffer();
        console.log(`Decoding ${arrayBuffer.byteLength} bytes of combined audio`);
        
        // Decode the audio data
        context.decodeAudioData(arrayBuffer, (decodedBuffer) => {
            console.log(`Successfully decoded audio: ${decodedBuffer.duration.toFixed(2)}s, ${decodedBuffer.sampleRate}Hz`);
            // Add the decoded buffer to the queue
            audioQueue.push(decodedBuffer);
            // If not currently playing, start processing the queue
            if (!isPlaying) {
                processAudioQueue();
            }
        }, (decodeError) => {
            console.error('Error decoding audio data:', decodeError);
            updateStatus('Error decoding audio response.', true);
            // Attempt to play next chunk if any
             if (!isPlaying) {
                 processAudioQueue();
             }
        });
    } catch (error) {
        console.error('Error processing audio blob:', error);
        updateStatus('Error processing audio response.', true);
    }
}

function processAudioQueue() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        console.log('Audio queue finished.');
        responseDiv.textContent = '(Audio playback complete)';
        updateStatus('Ready.');
        return;
    }

    isPlaying = true;
    const context = getAudioContext();
    const bufferToPlay = audioQueue.shift(); // Get the next buffer from the queue

    responseDiv.textContent = '(Playing audio...)';
    updateStatus('Playing audio response...');

    playbackSourceNode = context.createBufferSource();
    playbackSourceNode.buffer = bufferToPlay;
    playbackSourceNode.connect(context.destination);

    playbackSourceNode.onended = () => {
        console.log('Audio chunk finished playing.');
        // Automatically play the next chunk in the queue
        processAudioQueue();
    };

    playbackSourceNode.start(0); // Play immediately
}

// --- Initial State ---
resetUI();
updateStatus('Ready. Ensure backend URL in script.js points to the Docker host IP and mapped port.');

// Optional: Check for MediaRecorder support
if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
   updateStatus("getUserMedia not supported on your browser!", true);
   startButton.disabled = true;
   stopButton.disabled = true;
}
if (!window.MediaRecorder) {
    updateStatus("MediaRecorder not supported on your browser!", true);
    startButton.disabled = true;
    stopButton.disabled = true;
}
if (!window.WebSocket) {
     updateStatus("WebSockets not supported on your browser!", true);
     startButton.disabled = true;
     stopButton.disabled = true;
}
if (!window.AudioContext && !window.webkitAudioContext) {
     updateStatus("Web Audio API not supported on your browser!", true);
     // Playback might fail, but recording could still work
}
