const express = require('express');
const http = require('http');
const https = require('https'); // Added for HTTPS requests
const WebSocket = require('ws');
const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });
const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { Readable } = require('stream');
const temp = require('temp').track(); // Auto-cleanup temp files
const ffmpeg = require('fluent-ffmpeg');
const ffmpegInstaller = require('@ffmpeg-installer/ffmpeg');
const fetch = require('node-fetch');
const FormData = require('form-data'); // Added form-data package
const wav = require('node-wav');
require('dotenv').config(); // Load .env file variables

// Custom HTTPS agent with proper TLS configuration
const httpsAgent = new https.Agent({
    rejectUnauthorized: false, // Allow self-signed certificates - WARNING: This is insecure for production!
    keepAlive: true,
    timeout: 60000, // 60 seconds
    maxSockets: 100,
    secureOptions: require('constants').SSL_OP_NO_TLSv1 | require('constants').SSL_OP_NO_TLSv1_1, // Disable older TLS versions
    minVersion: 'TLSv1.2' // Ensure at least TLS 1.2 is used
});

// Set ffmpeg path
ffmpeg.setFfmpegPath(ffmpegInstaller.path);

// !!! CONFIGURATION !!!
const N8N_WEBHOOK_URL = process.env.N8N_WEBHOOK_URL || 'YOUR_N8N_WEBHOOK_RECEIVE_TEXT_URL'; // Replace with your n8n webhook URL
const BACKEND_RESPONSE_WEBHOOK_PATH = '/handle-n8n-response'; // Endpoint n8n calls on this backend
const PORT = process.env.BACKEND_PORT || 3000;

// STT and TTS API endpoints - default to localhost, but can be overridden from env vars
const WHISPER_API_URL = process.env.WHISPER_API_URL || 'http://whisper-api:9000/transcribe'; // Fixed Whisper API endpoint
const PIPER_API_URL = process.env.COQUI_TTS_API_URL || 'http://coqui-tts-api:5002/api/tts'; // Updated TTS API URL
// !!! END CONFIGURATION !!!

// Create temp directories for audio processing
const TEMP_DIR = temp.mkdirSync('audio-processing');
console.log(`[${new Date().toISOString()}] Temporary directory created: ${TEMP_DIR}`);

// Middleware for parsing JSON payloads
app.use(express.json());

// Endpoint for n8n to send back the AI response
app.post(BACKEND_RESPONSE_WEBHOOK_PATH, async (req, res) => {
    console.log(`[${new Date().toISOString()}] Received request on ${BACKEND_RESPONSE_WEBHOOK_PATH}`);
    console.log(`[${new Date().toISOString()}] Request Headers:`, JSON.stringify(req.headers, null, 2));
    console.log(`[${new Date().toISOString()}] Request Body:`, JSON.stringify(req.body, null, 2));

    const { sessionId, textResponse } = req.body;
    let client = null; // Declare client in a higher scope

    if (!sessionId || !textResponse) {
        console.error(`[${new Date().toISOString()}] Received invalid request on ${BACKEND_RESPONSE_WEBHOOK_PATH}: Missing sessionId or textResponse.`);
        return res.status(400).send('Missing sessionId or textResponse');
    }

    console.log(`[${new Date().toISOString()}] Received response for session ${sessionId}: "${textResponse}"`);    try {
        client = findWebSocketClient(sessionId); // Assign to the higher-scoped client
        
        if (!client || client.readyState !== WebSocket.OPEN) {
            console.log(`[${sessionId}] Client disconnected before TTS could start.`);
            return res.status(200).send('Client disconnected.');
        }        console.log(`[${sessionId}] Sending text to Coqui TTS API: ${PIPER_API_URL}`);
        const fetchOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: textResponse }),
            // Add timeout for TTS request - XTTS can take longer to process
            timeout: 180000  // 3 minute timeout (180 seconds)
        };
        
        // Add HTTPS agent if the URL is HTTPS
        if (PIPER_API_URL.startsWith('https://')) {
            fetchOptions.agent = httpsAgent;
        }
        
        const ttsResponse = await fetch(PIPER_API_URL, fetchOptions);

        if (!ttsResponse.ok) {
            const errorBody = await ttsResponse.text();
            throw new Error(`TTS API request failed with status ${ttsResponse.status}: ${errorBody}`);
        }

        console.log(`[${sessionId}] Receiving audio stream from TTS API...`);

        // Handle the response based on Content-Type
        const contentType = ttsResponse.headers.get('Content-Type');
        console.log(`[${sessionId}] TTS API Content-Type: ${contentType}`);        if (contentType && contentType.includes('audio/')) {
            // Handle as binary audio data
            console.log(`[${sessionId}] Processing audio stream from TTS API...`);            // Check if we have a readable stream
            if (!ttsResponse.body) {
                throw new Error('TTS API response body is empty.');
            }
            
            // Buffer the complete TTS response before sending
            const audioChunks = [];
            let chunkCount = 0;
            
            ttsResponse.body.on('data', (chunk) => {
                chunkCount++;
                console.log(`[${sessionId}] Main TTS: Received chunk ${chunkCount}, size: ${chunk.length} bytes`);
                audioChunks.push(chunk);
            });
            
            ttsResponse.body.on('end', () => {
                console.log(`[${sessionId}] TTS audio stream finished. Total chunks: ${chunkCount}`);
                if (client.readyState === WebSocket.OPEN && audioChunks.length > 0) {
                    // Combine all chunks into a single buffer
                    const completeAudio = Buffer.concat(audioChunks);
                    console.log(`[${sessionId}] Sending complete main TTS audio buffer (${completeAudio.length} bytes)`);
                    
                    // Send the complete audio as a single message
                    client.send(completeAudio);
                    
                    // Signal that audio is complete
                    client.send(JSON.stringify({ event: 'audioEnd' }));
                }
            });
            
            ttsResponse.body.on('error', (streamError) => {
                console.error(`[${sessionId}] Error in TTS audio stream:`, streamError);
                if (client.readyState === WebSocket.OPEN) {
                    client.send(JSON.stringify({ 
                        type: 'error', 
                        source: 'tts-stream', 
                        message: `Audio stream error: ${streamError.message}` 
                    }));
                }
            });
        } else {
            // Handle non-audio content (fallback)
            console.log(`[${sessionId}] TTS API returned non-audio content type: ${contentType}`);
            const responseText = await ttsResponse.text();
            console.log(`[${sessionId}] TTS API response: ${responseText}`);
            
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({ 
                    type: 'textResponse', 
                    text: textResponse,
                    error: 'TTS returned non-audio content'
                }));
            }
        }

        res.status(200).send('Response is being processed.');
    } catch (error) {
        console.error(`[${sessionId}] Error processing TTS response:`, error);
        if (client && client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({ type: 'error', source: 'tts', message: `TTS processing failed: ${error.message}` }));
        }
        res.status(500).send('Internal server error during audio processing.');
    }
});

// New helper function to handle direct responses (for fallbacks)
async function sendDirectResponse(sessionId, text) {
    console.log(`[${sessionId}] Sending direct response: "${text}"`);
    let client = null; // Declare client in a higher scope
    try {
        client = findWebSocketClient(sessionId); // Assign to the higher-scoped client
        if (client && client.readyState === WebSocket.OPEN) {
            // Always send a text response first, in case TTS fails
            client.send(JSON.stringify({
                type: 'textResponse', 
                text: text
            }));

            try {                console.log(`[${sessionId}] Sending direct response text to Coqui TTS API: "${text.substring(0, 50)}..."`);
                const directFetchOptions = {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text }),
                    // Add timeout to prevent hanging on network issues
                    timeout: 120000  // Increased to 2 minutes (120 seconds)
                };
                
                // Add HTTPS agent if the URL is HTTPS
                if (PIPER_API_URL.startsWith('https://')) {
                    directFetchOptions.agent = httpsAgent;
                }
                
                const ttsResponse = await fetch(PIPER_API_URL, directFetchOptions);

                if (!ttsResponse.ok) {
                    const errorBody = await ttsResponse.text();
                    throw new Error(`TTS API request failed with status ${ttsResponse.status}: ${errorBody}`);
                }                console.log(`[${sessionId}] Receiving audio stream for direct response...`);                if (!ttsResponse.body) {
                    throw new Error('TTS API response body is empty.');
                }

                // Buffer the complete TTS response before sending
                const audioChunks = [];
                let chunkCount = 0;
                
                ttsResponse.body.on('data', (chunk) => {
                    chunkCount++;
                    console.log(`[${sessionId}] Direct response: Received TTS chunk ${chunkCount}, size: ${chunk.length} bytes`);
                    audioChunks.push(chunk);
                });
                
                ttsResponse.body.on('end', () => {
                    console.log(`[${sessionId}] Direct response TTS audio stream finished. Total chunks: ${chunkCount}`);
                    if (client.readyState === WebSocket.OPEN && audioChunks.length > 0) {
                        // Combine all chunks into a single buffer
                        const completeAudio = Buffer.concat(audioChunks);
                        console.log(`[${sessionId}] Sending complete direct response audio buffer (${completeAudio.length} bytes)`);
                        
                        // Send the complete audio as a single message
                        client.send(completeAudio);
                        
                        // Signal that audio is complete
                        client.send(JSON.stringify({ event: 'audioEnd' }));
                    }
                });
                
                ttsResponse.body.on('error', (streamError) => {
                    console.error(`[${sessionId}] Error in direct response TTS stream:`, streamError);
                    if (client.readyState === WebSocket.OPEN) {
                        client.send(JSON.stringify({ 
                            type: 'error', 
                            source: 'tts-direct-stream', 
                            message: `Direct audio stream error: ${streamError.message}` 
                        }));
                    }
                });
            } catch (ttsError) {
                console.error(`[${sessionId}] Error processing direct response TTS:`, ttsError);
                // We already sent a text response above, so we don't need to do anything else here
            }
        }
    } catch (error) {
        console.error(`[${sessionId}] Error in sendDirectResponse:`, error);
        // Attempt to find the client again if it wasn't found or was closed
        const currentClient = client || findWebSocketClient(sessionId); 
        if (currentClient && currentClient.readyState === WebSocket.OPEN) {
            currentClient.send(JSON.stringify({ type: 'error', source: 'direct', message: `Error sending direct message: ${error.message}` }));
        }
    }
}

// WebSocket server for audio streams from clients
wss.on('connection', (ws, req) => {
    const sessionId = generateSessionId();
    ws.sessionId = sessionId;
    const clientIp = req.socket.remoteAddress;
    console.log(`[${new Date().toISOString()}] Client connected: ${sessionId} from ${clientIp}`);

    // Initialize STT processing for this client
    initializeSTTForSession(sessionId);

    ws.on('message', async (message) => {
        if (typeof message === 'string') {
            console.log(`[${new Date().toISOString()}] Message (string) from client ${sessionId}: ${message}`);
            try {
                const command = JSON.parse(message);
                if (command.event === 'audioEnd') {
                    console.log(`[${new Date().toISOString()}] Client ${sessionId} signaled audio end.`);
                    await finalizeSTTForSession(sessionId);
                }
            } catch (e) {
                console.warn(`[${new Date().toISOString()}] Invalid JSON message from ${sessionId}: ${message}`);
            }
            return;
        }

        processAudioChunkForSTT(sessionId, message);
    });

    ws.on('close', (code, reason) => {
        console.log(`[${new Date().toISOString()}] Client disconnected: ${sessionId}. Code: ${code}, Reason: ${reason ? reason.toString() : 'N/A'}`);
        cleanupSession(sessionId);
    });

    ws.on('error', (error) => {
        console.error(`[${new Date().toISOString()}] WebSocket error for session ${sessionId}:`, error);
        cleanupSession(sessionId);
    });
});

// --- Helper Functions ---

function generateSessionId() {
    return uuidv4();
}

function findWebSocketClient(sessionId) {
    for (const client of wss.clients) {
        if (client.sessionId === sessionId && client.readyState === WebSocket.OPEN) {
            return client;
        }
    }
    return null;
}

// --- STT Processing with Whisper ---

let sttProcessors = {};

function initializeSTTForSession(sessionId) {
    console.log(`[${new Date().toISOString()}] Initializing STT for session ${sessionId}.`);
    sttProcessors[sessionId] = {
        buffer: [],
        timeoutHandle: null,
        isProcessing: false,
        audioFilePath: null
    };
}

async function processAudioChunkForSTT(sessionId, chunk) {
    const session = sttProcessors[sessionId];
    if (!session || session.isProcessing) {
        return;
    }

    session.buffer.push(chunk);

    if (session.timeoutHandle) {
        clearTimeout(session.timeoutHandle);
    }
    
    session.timeoutHandle = setTimeout(async () => {
        console.log(`[${new Date().toISOString()}] Timeout reached for session ${sessionId}. Finalizing STT.`);
        await finalizeSTTForSession(sessionId);
    }, 1500);
}

async function finalizeSTTForSession(sessionId) {
    const session = sttProcessors[sessionId];
    if (!session || session.isProcessing || session.buffer.length === 0) {
        return;
    }

    session.isProcessing = true;
    if (session.timeoutHandle) {
        clearTimeout(session.timeoutHandle);
        session.timeoutHandle = null;
    }

    const audioData = Buffer.concat(session.buffer);
    session.buffer = [];

    try {
        console.log(`[${new Date().toISOString()}] Starting STT processing for session ${sessionId} with ${audioData.length} bytes.`);
        
        // Create a temporary file to store the audio
        const tempFilePath = path.join(TEMP_DIR, `audio_${sessionId}.wav`);
        await fs.writeFile(tempFilePath, audioData);
        console.log(`[${sessionId}] Audio saved to temporary file: ${tempFilePath}`);
        
        // Create a proper FormData object with the file
        const formData = new FormData();
        formData.append('file', fs.createReadStream(tempFilePath));
        
        console.log(`[${sessionId}] Sending audio to STT API: ${WHISPER_API_URL}`);
        const sttResponse = await fetch(WHISPER_API_URL, {
            method: 'POST',
            body: formData,
            headers: formData.getHeaders(), // Important: Include the headers from FormData
        });

        // Clean up the temporary file
        fs.unlink(tempFilePath)
            .catch(err => console.error(`[${sessionId}] Error deleting temp file: ${err}`));

        if (!sttResponse.ok) {
            const errorBody = await sttResponse.text();
            throw new Error(`STT API request failed with status ${sttResponse.status}: ${errorBody}`);
        }        const sttResult = await sttResponse.json();
        const transcribedText = sttResult.text || (sttResult.results && sttResult.results[0]?.transcript) || '';

        console.log(`[${sessionId}] Received transcription: "${transcribedText}"`);        if (transcribedText && N8N_WEBHOOK_URL) {
            try {
                console.log(`[${sessionId}] Sending transcription to n8n: ${N8N_WEBHOOK_URL}`);
                
                // Use a timeout of 10 seconds for the n8n webhook request
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 10000);
                  // Create a proper request with our custom agent
                const isHttpsUrl = N8N_WEBHOOK_URL.startsWith('https://');
                const requestOptions = {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sessionId: sessionId, text: transcribedText }),
                    signal: controller.signal,
                };

                // Only use the httpsAgent for HTTPS URLs
                if (isHttpsUrl) {
                    requestOptions.agent = httpsAgent;
                }
                
                console.log(`[${sessionId}] Sending request to n8n with ${isHttpsUrl ? 'HTTPS' : 'HTTP'} agent`);
                const n8nResponse = await fetch(N8N_WEBHOOK_URL, requestOptions)
                    .finally(() => clearTimeout(timeout));
                console.log(`[${sessionId}] n8n webhook response status: ${n8nResponse.status}`);
                
                if (!n8nResponse.ok) {
                    console.warn(`[${sessionId}] n8n webhook returned status: ${n8nResponse.status}`);
                    
                    // Even if n8n fails, we should respond to the user
                    const client = findWebSocketClient(sessionId);
                    if (client && client.readyState === WebSocket.OPEN) {
                        client.send(JSON.stringify({
                            type: 'directResponse',
                            text: `I received your message: "${transcribedText}", but I'm having trouble processing it. Please try again later.`
                        }));
                    }                }
            } catch (n8nError) {
                console.error(`[${sessionId}] Error sending to n8n webhook:`, n8nError);
                
                // Send a fallback response to the user
                const client = findWebSocketClient(sessionId);
                if (client && client.readyState === WebSocket.OPEN) {
                    // Use the fallback TTS response
                    await sendDirectResponse(sessionId, `I received your message: "${transcribedText}", but I'm currently unable to connect to the AI service. Please check your internet connection or try again later.`);
                }
            }
        } else if (!transcribedText) {
            console.log(`[${sessionId}] Empty transcription received. Not sending to n8n.`);
        } else {
            console.warn(`[${sessionId}] N8N_WEBHOOK_URL not set. Cannot send transcription.`);
        }
    } catch (error) {
        console.error(`[${sessionId}] Error processing audio or STT response:`, error);
        const client = findWebSocketClient(sessionId);
        if (client && client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({ type: 'error', source: 'stt', message: `STT processing failed: ${error.message}` }));
        }
    }

    session.isProcessing = false;
}

// --- Session Cleanup ---

function cleanupSession(sessionId) {
    console.log(`[${new Date().toISOString()}] Cleaning up session ${sessionId}.`);
    const session = sttProcessors[sessionId];
    if (session) {
        if (session.timeoutHandle) {
            clearTimeout(session.timeoutHandle);
        }
        
        if (session.audioFilePath && fs.existsSync(session.audioFilePath)) {
            fs.remove(session.audioFilePath)
                .catch(err => console.error(`[${new Date().toISOString()}] Error deleting temp file:`, err));
        }
    }
    delete sttProcessors[sessionId];
}

// --- Server Start ---

server.listen(PORT, () => {
    console.log(`[${new Date().toISOString()}] Backend running on http://localhost:${PORT}`);
    console.log(`[${new Date().toISOString()}] WebSocket Server listening on ws://localhost:${PORT}`);
    console.log(`[${new Date().toISOString()}] n8n Callback Endpoint should target: POST http://10.10.1.106:${PORT}${BACKEND_RESPONSE_WEBHOOK_PATH}`);
    console.log(`[${new Date().toISOString()}] n8n should send transcriptions to this Webhook: ${N8N_WEBHOOK_URL}`);
    console.log(`[${new Date().toISOString()}] Using Whisper API at: ${WHISPER_API_URL}`);
    console.log(`[${new Date().toISOString()}] Using Piper TTS API at: ${PIPER_API_URL}`);
    
    if (N8N_WEBHOOK_URL === 'YOUR_N8N_WEBHOOK_RECEIVE_TEXT_URL') {
        console.warn(`[${new Date().toISOString()}] WARNING: N8N_WEBHOOK_URL is not set in the environment variables or .env file!`);
    }
});

// Graceful Shutdown
process.on('SIGTERM', () => {
    console.log(`[${new Date().toISOString()}] SIGTERM signal received: closing HTTP server`);
    server.close(() => {
        console.log(`[${new Date().toISOString()}] HTTP server closed`);
        wss.close(() => {
             console.log(`[${new Date().toISOString()}] WebSocket server closed`);
             process.exit(0);
        });
    });
});

process.on('SIGINT', () => {
     console.log(`[${new Date().toISOString()}] SIGINT signal received: closing HTTP server`);
    server.close(() => {
        console.log(`[${new Date().toISOString()}] HTTP server closed`);
         wss.close(() => {
             console.log(`[${new Date().toISOString()}] WebSocket server closed`);
             process.exit(0);
        });
    });
});
