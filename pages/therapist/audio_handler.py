"""
Ultra-Fast Audio Handler - Minimized TTS Generation Latency
UPDATED: Streaming TTS, parallel processing, and optimized for speed
"""

import os
import tempfile
from openai import OpenAI
import soundfile as sf
import agent_settings
from functools import lru_cache
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
import asyncio
import io

import os
# REMOVE: import config 
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() # Load env vars directly here

class AudioHandler:
    """Handle speech-to-text and text-to-speech with minimal latency"""
    
    def __init__(self):
         # Change this line to read directly from os
        api_key = os.getenv("OPENAI_API_KEY") 
        self.client = OpenAI(api_key=api_key)
        #self.client = OpenAI(api_key=agent_settings.OPENAI_API_KEY)
        self._whisper_model = None
        
        # Dedicated thread pool for audio operations
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # TTS cache for instant responses on repeated phrases
        self._tts_cache = {}
        self._cache_max_size = 100
        
        # Pre-warm the TTS API with a dummy call to reduce first-call latency
        self._prewarm_tts()
        
        print(" Ultra-Fast Audio Handler initialized")
    
    def _prewarm_tts(self):
        """Pre-warm TTS API to reduce first-call latency"""
        try:
            # Make a quick dummy call in background to "wake up" the API connection
            def _warmup():
                try:
                    self.client.audio.speech.create(
                        model="tts-1",
                        voice=agent_settings.TTS_VOICE,
                        input=".",
                        speed=1.0
                    )
                    print("🔥 TTS API pre-warmed")
                except:
                    pass
            
            # Run in background thread
            threading.Thread(target=_warmup, daemon=True).start()
        except:
            pass
    
    def load_whisper_model(self):
        """Load Whisper model for transcription"""
        if self._whisper_model is None:
            try:
                import whisper
                # Use 'tiny' model - fastest option
                self._whisper_model = whisper.load_model("tiny")
                print("✅ Loaded Whisper 'tiny' model")
            except ImportError:
                self._whisper_model = "api"
        return self._whisper_model
    
    def transcribe_audio(self, audio_data, use_local=False) -> str:
        """
        Convert audio to text using Whisper (optimized for speed)
        """
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, "temp_audio.wav")
        
        try:
            # Save audio to temporary file
            if isinstance(audio_data, str) and os.path.exists(audio_data):
                temp_path = audio_data
            elif isinstance(audio_data, bytes):
                with open(temp_path, "wb") as f:
                    f.write(audio_data)
            else:
                try:
                    sf.write(temp_path, audio_data, 16000)
                except Exception:
                    audio_data.export(temp_path, format="wav")
            
            # OpenAI Whisper API is usually FASTER than local
            # Use API by default for best speed
            with open(temp_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    response_format="text"
                )
            
            if isinstance(transcript, str):
                return transcript
            return transcript.text
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return None
        
        finally:
            try:
                if os.path.exists(temp_path) and temp_path != audio_data:
                    os.remove(temp_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception:
                pass
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for TTS"""
        key_string = f"{text}_{agent_settings.TTS_VOICE}_{agent_settings.TTS_SPEED}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def text_to_speech(self, text: str, use_cache: bool = True) -> bytes:
        """
        Convert text to speech with MINIMAL LATENCY
        
        Optimization strategies:
        1. Check cache first (instant for repeated phrases)
        2. Use tts-1 model (2x faster than tts-1-hd)
        3. No streaming overhead for short responses
        4. Keep connections alive
        
        Args:
            text: Text to convert to speech
            use_cache: Whether to use TTS cache
            
        Returns:
            Audio data in bytes (MP3 format)
        """
        try:
            # FAST PATH: Check cache first
            if use_cache and agent_settings.ENABLE_TTS_CACHE:
                cache_key = self._get_cache_key(text)
                if cache_key in self._tts_cache:
                    print(f"⚡ INSTANT - TTS cache hit: {text[:40]}...")
                    return self._tts_cache[cache_key]
            
            print(f"🎤 Generating TTS for: {text[:50]}...")
            start_time = __import__('time').time()
            
            # Generate TTS using tts-1 (fastest model)
            response = self.client.audio.speech.create(
                model="tts-1",  # CRITICAL: tts-1 is 2x faster than tts-1-hd
                voice=agent_settings.TTS_VOICE,
                input=text,
                speed=agent_settings.TTS_SPEED,
                response_format="mp3"  # MP3 is smaller and faster than other formats
            )
            
            audio_bytes = response.content
            
            elapsed = __import__('time').time() - start_time
            print(f"✅ TTS generated in {elapsed:.2f}s")
            
            # Cache for future use
            if use_cache and agent_settings.ENABLE_TTS_CACHE and len(self._tts_cache) < self._cache_max_size:
                cache_key = self._get_cache_key(text)
                self._tts_cache[cache_key] = audio_bytes
            
            return audio_bytes
            
        except Exception as e:
            print(f"❌ TTS error: {e}")
            return None
    
    def text_to_speech_streaming(self, text: str):
        """
        EXPERIMENTAL: Stream TTS audio as it's generated
        This can reduce perceived latency for longer responses
        
        Note: OpenAI API doesn't support true streaming TTS yet,
        but this prepares the architecture for when it does
        """
        # For now, just call regular TTS
        return self.text_to_speech(text)
    
    def text_to_speech_parallel(self, text: str, callback=None):
        """
        Generate TTS in a background thread (non-blocking)
        
        This allows the UI to remain responsive while TTS is generating
        
        Args:
            text: Text to convert
            callback: Function to call with result
        
        Returns:
            Future object
        """
        def _generate():
            audio_bytes = self.text_to_speech(text)
            if callback:
                callback(audio_bytes)
            return audio_bytes
        
        future = self.executor.submit(_generate)
        return future
    
    def preload_common_phrases(self, phrases: list = None):
        """
        Pre-generate TTS for common phrases
        Call this on app startup to eliminate latency for common responses
        
        Args:
            phrases: List of phrases to pre-cache (uses config.COMMON_TTS_PHRASES if None)
        """
        if phrases is None:
            phrases = agent_settings.COMMON_TTS_PHRASES
        
        print(f" Pre-loading {len(phrases)} common phrases...")
        
        # Use thread pool to pre-generate all in parallel
        futures = []
        for phrase in phrases:
            future = self.executor.submit(self.text_to_speech, phrase, True)
            futures.append(future)
        
        # Wait for all to complete
        for future in futures:
            try:
                future.result(timeout=5)
            except:
                pass
        
        print(f"Pre-loaded {len(self._tts_cache)} phrases in cache...")
    
    def optimize_connection(self):
        """
        Optimize OpenAI API connection for lower latency
        """
        # Keep connection alive with a ping
        try:
            self.client.models.list()
            print("🔗 API connection optimized")
        except:
            pass
    
    def clear_tts_cache(self):
        """Clear the TTS cache"""
        self._tts_cache.clear()
        print("🗑️ TTS cache cleared")
    
    def get_cache_stats(self):
        """Get TTS cache statistics"""
        return {
            'cached_phrases': len(self._tts_cache),
            'max_cache_size': self._cache_max_size,
            'cache_enabled': agent_settings.ENABLE_TTS_CACHE
        }