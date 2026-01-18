// Example: WebSocket Audio Streaming with Dynamic Language Selection
// This example demonstrates how to connect and stream audio with different languages

import io from 'socket.io-client';

/**
 * Supported languages for Deepgram Nova-2 transcription
 */
const SUPPORTED_LANGUAGES = [
  'en', 'es', 'fr', 'it', 'de', 'pt', 'nl', 'hi', 'ja', 'ko',
  'zh', 'sv', 'no', 'da', 'fi', 'pl', 'ru', 'tr', 'ar', 'el',
  'he', 'cs', 'uk', 'ro', 'hu', 'id', 'ms', 'th', 'vi'
];

/**
 * AudioStreamClient - Manages WebSocket connection for real-time transcription
 */
class AudioStreamClient {
  constructor(serverUrl, authToken, language = 'en') {
    this.serverUrl = serverUrl;
    this.authToken = authToken;
    this.language = language;
    this.socket = null;
    this.isConnected = false;
    this.confirmedLanguage = null;
    
    // Event callbacks
    this.onConnected = null;
    this.onTranscription = null;
    this.onError = null;
    this.onDisconnected = null;
  }

  /**
   * Connect to WebSocket with specified language
   */
  connect() {
    return new Promise((resolve, reject) => {
      // Validate language
      if (!SUPPORTED_LANGUAGES.includes(this.language)) {
        console.warn(
          `Language '${this.language}' not supported. Defaulting to 'en'`
        );
        this.language = 'en';
      }

      // Create Socket.IO client with language parameter
      this.socket = io(`${this.serverUrl}/audio-stream`, {
        auth: {
          token: this.authToken
        },
        query: {
          lang: this.language
        },
        transports: ['websocket']
      });

      // Connection successful
      this.socket.on('connect', () => {
        console.log('WebSocket connected');
      });

      // Server confirms connection with language
      this.socket.on('connected', (data) => {
        this.isConnected = true;
        this.confirmedLanguage = data.language;
        
        console.log('Connection confirmed:', data);
        console.log(`Language: ${data.language}`);
        
        if (this.onConnected) {
          this.onConnected(data);
        }
        
        resolve(data);
      });

      // Transcription results
      this.socket.on('transcription', (data) => {
        if (this.onTranscription) {
          this.onTranscription(data);
        }
      });

      // Error handling
      this.socket.on('error', (data) => {
        console.error('WebSocket error:', data);
        
        if (this.onError) {
          this.onError(data);
        }
        
        reject(new Error(data.message || 'Connection error'));
      });

      // Disconnection
      this.socket.on('disconnect', (reason) => {
        this.isConnected = false;
        console.log('Disconnected:', reason);
        
        if (this.onDisconnected) {
          this.onDisconnected(reason);
        }
      });

      // Connection timeout
      setTimeout(() => {
        if (!this.isConnected) {
          reject(new Error('Connection timeout'));
        }
      }, 10000);
    });
  }

  /**
   * Send audio data to server for transcription
   * @param {ArrayBuffer|Blob|string} audioData - Audio data (base64 string or binary)
   */
  sendAudio(audioData) {
    if (!this.isConnected) {
      throw new Error('Not connected to WebSocket');
    }

    // Convert to base64 if needed
    let base64Audio;
    
    if (typeof audioData === 'string') {
      base64Audio = audioData;
    } else if (audioData instanceof Blob) {
      // For Blob, need to convert (async)
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = btoa(reader.result);
          this.socket.emit('audio_data', base64);
          resolve();
        };
        reader.onerror = reject;
        reader.readAsBinaryString(audioData);
      });
    } else if (audioData instanceof ArrayBuffer) {
      // Convert ArrayBuffer to base64
      const binary = new Uint8Array(audioData);
      base64Audio = btoa(String.fromCharCode(...binary));
    } else {
      throw new Error('Unsupported audio data type');
    }

    this.socket.emit('audio_data', base64Audio);
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.isConnected = false;
    }
  }

  /**
   * Change language (requires reconnection)
   */
  async changeLanguage(newLanguage) {
    this.language = newLanguage;
    this.disconnect();
    return this.connect();
  }
}

// ============================================================================
// EXAMPLE 1: Basic Usage
// ============================================================================

async function example1_BasicUsage() {
  const client = new AudioStreamClient(
    'wss://your-api.com',
    'your-auth-token',
    'it' // Italian
  );

  // Setup event handlers
  client.onConnected = (data) => {
    console.log('Connected!', data);
    console.log('Transcribing in:', data.language);
  };

  client.onTranscription = (data) => {
    if (data.is_final) {
      console.log('Final:', data.transcript);
    } else {
      console.log('Interim:', data.transcript);
    }
  };

  client.onError = (error) => {
    console.error('Error:', error);
  };

  // Connect
  await client.connect();

  // Send audio (mock data)
  const mockAudioData = new ArrayBuffer(1024);
  await client.sendAudio(mockAudioData);

  // Disconnect when done
  setTimeout(() => {
    client.disconnect();
  }, 5000);
}

// ============================================================================
// EXAMPLE 2: Microphone Streaming
// ============================================================================

async function example2_MicrophoneStreaming(language = 'en') {
  const client = new AudioStreamClient(
    'wss://your-api.com',
    'your-auth-token',
    language
  );

  // Connect to WebSocket
  await client.connect();

  // Get microphone access
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      sampleRate: 16000
    }
  });

  // Setup audio processing
  const audioContext = new AudioContext({ sampleRate: 16000 });
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);

  source.connect(processor);
  processor.connect(audioContext.destination);

  // Process audio chunks
  processor.onaudioprocess = (event) => {
    const audioData = event.inputBuffer.getChannelData(0);
    
    // Convert Float32Array to Int16 (required by Deepgram)
    const int16Data = new Int16Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      int16Data[i] = Math.max(-32768, Math.min(32767, audioData[i] * 32768));
    }

    // Send to WebSocket
    client.sendAudio(int16Data.buffer);
  };

  // Display transcriptions
  client.onTranscription = (data) => {
    if (data.is_final) {
      console.log(`[${language.toUpperCase()}] ${data.transcript}`);
    }
  };

  // Stop after 10 seconds
  setTimeout(() => {
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach(track => track.stop());
    client.disconnect();
  }, 10000);
}

// ============================================================================
// EXAMPLE 3: Multi-Language Support (Language Selector UI)
// ============================================================================

async function example3_LanguageSelector() {
  const languageOptions = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Spanish' },
    { code: 'fr', name: 'French' },
    { code: 'it', name: 'Italian' },
    { code: 'de', name: 'German' },
    { code: 'pt', name: 'Portuguese' },
    { code: 'zh', name: 'Chinese' }
  ];

  let currentClient = null;
  let currentLanguage = 'en';

  // Create language selector UI
  const selector = document.createElement('select');
  selector.id = 'language-selector';
  
  languageOptions.forEach(option => {
    const opt = document.createElement('option');
    opt.value = option.code;
    opt.textContent = option.name;
    selector.appendChild(opt);
  });

  // Language change handler
  selector.addEventListener('change', async (event) => {
    const newLanguage = event.target.value;
    
    if (currentClient) {
      console.log(`Switching from ${currentLanguage} to ${newLanguage}`);
      
      // Disconnect old client
      currentClient.disconnect();
      
      // Create new client with new language
      currentClient = new AudioStreamClient(
        'wss://your-api.com',
        'your-auth-token',
        newLanguage
      );
      
      // Reconnect
      await currentClient.connect();
      currentLanguage = newLanguage;
      
      console.log(`Now transcribing in ${newLanguage}`);
    }
  });

  // Initial connection
  currentClient = new AudioStreamClient(
    'wss://your-api.com',
    'your-auth-token',
    currentLanguage
  );
  
  await currentClient.connect();
}

// ============================================================================
// EXAMPLE 4: React Component
// ============================================================================

/*
import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';

const AudioTranscription = ({ serverUrl, authToken }) => {
  const [language, setLanguage] = useState('en');
  const [transcript, setTranscript] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    // Connect to WebSocket with selected language
    const socket = io(`${serverUrl}/audio-stream`, {
      auth: { token: authToken },
      query: { lang: language },
      transports: ['websocket']
    });

    socket.on('connect', () => {
      console.log('Connected');
    });

    socket.on('connected', (data) => {
      setIsConnected(true);
      console.log('Language confirmed:', data.language);
    });

    socket.on('transcription', (data) => {
      if (data.is_final) {
        setTranscript(prev => prev + ' ' + data.transcript);
      }
    });

    socket.on('error', (error) => {
      console.error('Error:', error);
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, [language, serverUrl, authToken]);

  return (
    <div>
      <select value={language} onChange={(e) => setLanguage(e.target.value)}>
        <option value="en">English</option>
        <option value="es">Spanish</option>
        <option value="it">Italian</option>
        <option value="fr">French</option>
      </select>
      
      <div>Status: {isConnected ? 'Connected' : 'Disconnected'}</div>
      <div>Language: {language}</div>
      <div>Transcript: {transcript}</div>
    </div>
  );
};

export default AudioTranscription;
*/

// ============================================================================
// Export for module usage
// ============================================================================

export {
  AudioStreamClient,
  SUPPORTED_LANGUAGES
};
