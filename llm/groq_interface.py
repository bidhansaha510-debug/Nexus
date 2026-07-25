"""
NEXUS AI - Groq API Interface
OpenAI-compatible interface to Groq's fast LLM inference API.
Used specifically for generating user-facing responses.
"""

import requests
import json
import copy
import threading
import time
from typing import Dict, List, Any, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import sys
from utils.logger import get_logger

logger = get_logger("groq_interface")

# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GroqResponse:
    """Response from Groq API"""
    text: str = ""
    model: str = ""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    success: bool = True
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    latency_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "model": self.model,
            "total_tokens": self.total_tokens,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "latency_seconds": self.latency_seconds
        }

# ═══════════════════════════════════════════════════════════════════════════════
# GROQ INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class GroqInterface:
    """
    Interface to Groq's OpenAI-compatible API.
    
    This is used specifically for generating user-facing responses,
    while the local Ollama handles internal tasks like code fixing,
    curiosity engine, feature research, etc.
    
    Groq provides ultra-fast inference for Llama models.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        from config import NEXUS_CONFIG
        self._config = NEXUS_CONFIG.groq
        
        # ──── Groq API Configuration ────
        self._api_key = self._config.api_key
        # Fallback list of api keys
        self._api_keys = getattr(self._config, 'api_keys', [])
        if not self._api_keys and self._api_key:
            self._api_keys = [self._api_key]
        self._current_key_idx = 0
            
        self._base_url = self._config.base_url
        self._model = self._config.model
        
        # Default generation parameters
        self._temperature = self._config.temperature
        self._max_tokens = self._config.max_tokens
        self._top_p = self._config.top_p
        
        # Connection state
        self._connected = False
        self._last_check = None
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens_generated": 0,
            "average_latency": 0.0
        }
        
        # Request history
        self._request_history: List[Dict] = []
        self._max_history = 100
        
        # Test connection
        self._check_connection()
        
        logger.info(f"Groq Interface initialized - Model: {self._model}, Keys: {len(self._api_keys)}")
        
    def _rotate_key(self) -> bool:
        """Rotate to the next API key in the pool"""
        if not self._api_keys or len(self._api_keys) <= 1:
            logger.warning("Groq rate limit hit, but no alternative keys in pool to rotate to.")
            return False
            
        old_idx = self._current_key_idx
        self._current_key_idx = (self._current_key_idx + 1) % len(self._api_keys)
        # safe logging
        old_key = self._api_keys[old_idx][:8] + "..." if len(self._api_keys[old_idx]) > 8 else "..."
        new_key = self._api_keys[self._current_key_idx][:8] + "..." if len(self._api_keys[self._current_key_idx]) > 8 else "..."
        
        logger.warning(f"🔄 Rotating Groq API Key: {old_key} -> {new_key}")
        return True
    
    def _get_current_key(self) -> str:
        """Helper to safely get the current API key"""
        if not self._api_keys:
            return self._api_key or ""
        return self._api_keys[self._current_key_idx]
    
    def _check_connection(self) -> bool:
        """Check if Groq API is accessible"""
        # If we have an API key, assume connected and let actual requests handle failures
        if self._get_current_key():
            self._connected = True
            if self._last_check is None: # only log on first connect
                logger.info("✅ Groq API ready (API key configured)")
            self._last_check = datetime.now()
            return True
        
        self._connected = False
        logger.error("❌ No Groq API key configured")
        self._last_check = datetime.now()
        return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication"""
        return {
            "Authorization": f"Bearer {self._get_current_key()}",
            "Content-Type": "application/json"
        }
    
    @property
    def is_connected(self) -> bool:
        """Check if connected (with caching)"""
        if self._last_check:
            elapsed = (datetime.now() - self._last_check).total_seconds()
            if elapsed < 60:  # Cache for 60 seconds
                return self._connected
        return self._check_connection()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHAT COMPLETION METHODS (OpenAI-compatible)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        stop: List[str] = None,
        images: List[str] = None
    ) -> GroqResponse:
        """
        Chat-style interaction using OpenAI-compatible chat/completions endpoint.
        
        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            system_prompt: System instructions (prepended to messages if provided)
            temperature: Creativity (0-2)
            max_tokens: Max response tokens
            top_p: Nucleus sampling
            stop: Stop sequences
            
        Returns:
            GroqResponse object
        """
        if not self.is_connected:
            return GroqResponse(
                success=False,
                error="Not connected to Groq API"
            )
        
        self._stats["total_requests"] += 1
        
        try:
            # Build message list — deep copy to avoid mutating the caller's data
            msg_list = copy.deepcopy(messages)
            
            has_images = False
            if images:
                has_images = True
                for msg in reversed(msg_list):
                    if msg.get("role") == "user":
                        text = msg.get("content", "")
                        if isinstance(text, list):
                            # Already multimodal — extract text part
                            text = next((p.get("text", "") for p in text if p.get("type") == "text"), "")
                        content_list = [{"type": "text", "text": text}]
                        for img in images:
                            content_list.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img}"}
                            })
                        msg["content"] = content_list
                        break
            else:
                # Ensure all message contents are plain strings
                for msg in msg_list:
                    if isinstance(msg.get("content"), list):
                        # Extract text from multimodal content that leaked in
                        parts = msg["content"]
                        msg["content"] = next(
                            (p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"),
                            str(parts)
                        )
            
            if system_prompt:
                # Insert system prompt at the beginning
                msg_list = [{"role": "system", "content": system_prompt}] + msg_list
            
            payload = {
                "model": "meta-llama/llama-4-scout-17b-16e-instruct" if has_images else self._model,
                "messages": msg_list,
                "temperature": temperature if temperature is not None else self._temperature,
                "max_tokens": max_tokens or self._max_tokens,
                "top_p": top_p or self._top_p,
            }
            
            if stop:
                payload["stop"] = stop
            
            max_retries = max(1, len(self._api_keys))
            for attempt in range(max_retries):
                start_time = time.time()
                
                response = requests.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=None  # No time limit
                )
                
                elapsed = time.time() - start_time
                
                if response.status_code == 429:
                    if attempt < max_retries - 1 and self._rotate_key():
                        continue # Retry immediately with new key
                    else:
                        error_msg = "Rate limit exceeded on all available Groq API keys."
                        self._stats["failed_requests"] += 1
                        logger.error(error_msg)
                        return GroqResponse(success=False, error=error_msg)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract response
                    choices = data.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content") or ""
                    else:
                        content = ""
                    
                    # Extract usage
                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    
                    groq_response = GroqResponse(
                        text=content,
                        model=data.get("model", self._model),
                        total_tokens=total_tokens,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        success=True,
                        latency_seconds=elapsed
                    )
                    
                    self._stats["successful_requests"] += 1
                    self._stats["total_tokens_generated"] += completion_tokens
                    
                    # Update average latency
                    current_avg = self._stats["average_latency"]
                    total_success = self._stats["successful_requests"]
                    self._stats["average_latency"] = (
                        (current_avg * (total_success - 1) + elapsed) / total_success
                    )
                    
                    logger.info(
                        f"Groq Response: {completion_tokens} tokens in {elapsed:.2f}s "
                        f"(total: {total_tokens} tokens)"
                    )
                    
                    # Record history
                    self._record_request(messages, groq_response)
                    
                    return groq_response
                else:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_msg = error_data.get("error", {}).get("message", f"API error: {response.status_code}")
                    
                    self._stats["failed_requests"] += 1
                    logger.error(f"Groq API error: {error_msg}")
                    return GroqResponse(success=False, error=error_msg)
            
            # If all retries fail
            self._stats["failed_requests"] += 1
            return GroqResponse(success=False, error="Failed after max retries")
                
        except requests.Timeout:
            self._stats["failed_requests"] += 1
            error_msg = "Request timed out"
            logger.error(error_msg)
            return GroqResponse(success=False, error=error_msg)
            
        except requests.ConnectionError:
            self._stats["failed_requests"] += 1
            error_msg = "Connection error - network unavailable"
            logger.error(error_msg)
            return GroqResponse(success=False, error=error_msg)
            
        except Exception as e:
            self._stats["failed_requests"] += 1
            error_msg = f"Generation error: {str(e)}"
            logger.error(error_msg)
            return GroqResponse(success=False, error=error_msg)
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        stop: List[str] = None,
        images: List[str] = None
    ) -> Generator[str, None, None]:
        """
        Stream chat responses token by token.
        
        Yields tokens as they're generated for real-time display.
        """
        if not self.is_connected:
            yield "[Error: Not connected to Groq API]"
            return
        
        self._stats["total_requests"] += 1
        
        try:
            # Build message list — deep copy to avoid mutating the caller's data
            msg_list = copy.deepcopy(messages)
            
            has_images = False
            if images:
                has_images = True
                for msg in reversed(msg_list):
                    if msg.get("role") == "user":
                        text = msg.get("content", "")
                        if isinstance(text, list):
                            text = next((p.get("text", "") for p in text if p.get("type") == "text"), "")
                        content_list = [{"type": "text", "text": text}]
                        for img in images:
                            content_list.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img}"}
                            })
                        msg["content"] = content_list
                        break
            else:
                for msg in msg_list:
                    if isinstance(msg.get("content"), list):
                        parts = msg["content"]
                        msg["content"] = next(
                            (p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"),
                            str(parts)
                        )
            
            if system_prompt:
                msg_list = [{"role": "system", "content": system_prompt}] + msg_list
            
            payload = {
                "model": "meta-llama/llama-4-scout-17b-16e-instruct" if has_images else self._model,
                "messages": msg_list,
                "temperature": temperature if temperature is not None else self._temperature,
                "max_tokens": max_tokens or self._max_tokens,
                "top_p": top_p or self._top_p,
                "stream": True
            }
            
            if stop:
                payload["stop"] = stop
            
            max_retries = max(1, len(self._api_keys))
            for attempt in range(max_retries):
                response = requests.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                    stream=True,
                    timeout=None  # No time limit
                )
                
                if response.status_code == 429:
                    if attempt < max_retries - 1 and self._rotate_key():
                        continue # Retry immediately with new key
                    else:
                        self._stats["failed_requests"] += 1
                        yield "[Error: Rate limit exceeded on all available Groq API keys.]"
                        return
                
                if response.status_code == 200:
                    full_response = ""
                    
                    for line in response.iter_lines():
                        if line:
                            line_text = line.decode('utf-8')
                            
                            # Skip SSE keep-alive
                            if line_text == "data: [DONE]":
                                break
                            
                            if line_text.startswith("data: "):
                                try:
                                    data = json.loads(line_text[6:])
                                    choices = data.get("choices", [])
                                    
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        token = delta.get("content", "")
                                        
                                        if token:
                                            full_response += token
                                            yield token
                                            
                                except json.JSONDecodeError:
                                    continue
                    
                    self._stats["successful_requests"] += 1
                    self._stats["total_tokens_generated"] += len(full_response.split())
                    return # Exit loop once successfully streamed
                    
                else:
                    self._stats["failed_requests"] += 1
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_msg = error_data.get("error", {}).get("message", f"API error: {response.status_code}")
                    yield f"[Error: Groq API returned status {response.status_code} - {error_msg}]"
                    return
            
            # If all retries fail
            self._stats["failed_requests"] += 1
            yield "[Error: Failed after max retries]"
            return
                
        except Exception as e:
            self._stats["failed_requests"] += 1
            yield f"[Error: {str(e)}]"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIMPLE GENERATION (for convenience)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = None,
        max_tokens: int = None
    ) -> GroqResponse:
        """
        Simple generation from a single prompt.
        
        Converts to chat format internally.
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _record_request(self, messages: List[Dict], response: GroqResponse):
        """Record request in history"""
        self._request_history.append({
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "response_length": len(response.text) if response.text is not None else 0,
            "tokens": response.total_tokens,
            "latency": response.latency_seconds,
            "success": response.success
        })
        
        if len(self._request_history) > self._max_history:
            self._request_history.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            **self._stats,
            "connected": self._connected,
            "model": self._model,
            "base_url": self._base_url
        }
    
    def list_models(self) -> List[str]:
        """List available models from Groq"""
        try:
            response = requests.get(
                f"{self._base_url}/models",
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                return [m.get("id", "") for m in models]
        except Exception as e:
            logger.debug(f"Could not list models: {e}")
        
        return [self._model]  # Return default model if API fails
    
    def set_model(self, model_name: str) -> bool:
        """Switch to a different model"""
        self._model = model_name
        logger.info(f"Switched to model: {model_name}")
        return True
    
    def set_temperature(self, temperature: float):
        """Set default temperature"""
        self._temperature = max(0.0, min(2.0, temperature))
    
    def set_max_tokens(self, max_tokens: int):
        """Set default max tokens"""
        self._max_tokens = max_tokens

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

groq_interface = GroqInterface()

if __name__ == "__main__":
    interface = GroqInterface()
    
    print(f"Connected: {interface.is_connected}")
    print(f"Available models: {interface.list_models()}")
    
    if interface.is_connected:
        # Test chat
        print("\n--- Testing Chat ---")
        response = interface.chat(
            messages=[{"role": "user", "content": "Hello! Tell me a short joke."}],
            system_prompt="You are a friendly AI named NEXUS.",
            temperature=0.7
        )
        print(f"Response: {response.text}")
        print(f"Tokens: {response.total_tokens}")
        print(f"Latency: {response.latency_seconds:.2f}s")
        
        print(f"\nStats: {interface.get_stats()}")
    else:
        print("\n⚠️ Groq API connection failed. Check your API key.")