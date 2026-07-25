"""
NEXUS AI - Llama 3 LLM Interface
Connection to local Ollama instance running Llama 3
"""

import requests
import json
import threading
import time
from typing import Dict, List, Any, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import sys
from config import NEXUS_CONFIG
from utils.logger import get_logger

logger = get_logger("llama_interface")

# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LLMResponse:
    """Response from LLM"""
    text: str = ""
    model: str = ""
    total_duration: float = 0.0
    load_duration: float = 0.0
    prompt_eval_count: int = 0
    eval_count: int = 0
    eval_duration: float = 0.0
    tokens_per_second: float = 0.0
    success: bool = True
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "model": self.model,
            "total_duration": self.total_duration,
            "tokens_per_second": self.tokens_per_second,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }

# ═══════════════════════════════════════════════════════════════════════════════
# LLAMA INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LlamaInterface:
    """
    Interface to local Llama 3 via Ollama
    Handles all LLM interactions
    """
    
    _instance = None
    _lock = threading.Lock()
    _thread_local = threading.local()
    # Limit concurrent Ollama requests to prevent 429 overload
    _ollama_semaphore = threading.Semaphore(2)
    _MAX_RETRIES = 3
    _RETRY_BASE_DELAY = 2.0  # seconds, doubles each retry
    _HEALTH_CHECK_TIMEOUT = 15  # seconds — generous to avoid false negatives when Ollama is busy
    _HEALTH_CHECK_RETRIES = 3   # retry transient failures before marking disconnected
    _HEALTH_CACHE_TTL = 120     # seconds — cache "connected" state to avoid hammering Ollama
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def force_groq(self, state: bool):
        """Force use of Groq API for this thread (useful for fast cognitive routing)"""
        self._thread_local.use_groq = state
        
    def should_use_groq(self) -> bool:
        return getattr(self._thread_local, "use_groq", False)
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._config = NEXUS_CONFIG.llm
        self._base_url = self._config.base_url
        self._model = self._config.model_name
        
        # Connection state
        self._connected = False
        self._last_check = None
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens_generated": 0,
            "average_tokens_per_second": 0.0
        }
        
        # Request history
        self._request_history: List[Dict] = []
        self._max_history = 100
        
        # Check connection
        self._check_connection()
    
    def _check_connection(self) -> bool:
        """Check if Ollama is running and model is available.
        
        Retries up to _HEALTH_CHECK_RETRIES times with exponential backoff
        to avoid false-negative disconnections when Ollama is simply busy
        processing a large request.
        """
        last_error = None
        for attempt in range(self._HEALTH_CHECK_RETRIES):
            try:
                response = requests.get(
                    f"{self._base_url}/api/tags",
                    timeout=self._HEALTH_CHECK_TIMEOUT
                )
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m["name"] for m in models]
                    
                    if any(self._model.split(":")[0] in name for name in model_names):
                        self._connected = True
                        self._last_check = datetime.now()
                        # Only log on state change to avoid log spam
                        logger.debug(f"✅ Connected to Ollama. Model '{self._model}' available.")
                        return True
                    else:
                        self._connected = False
                        available = ", ".join(model_names) if model_names else "none"
                        logger.warning(
                            f"⚠️ Model '{self._model}' not found. Available: {available}. "
                            f"Run: ollama pull {self._model}"
                        )
                        self._last_check = datetime.now()
                        return False
                else:
                    last_error = f"Ollama responded with status {response.status_code}"
                    
            except requests.Timeout:
                last_error = "Health check timed out (Ollama may be busy)"
            except requests.ConnectionError:
                last_error = "Connection refused"
            except Exception as e:
                last_error = str(e)
            
            # Retry with backoff — but only if we have attempts left
            if attempt < self._HEALTH_CHECK_RETRIES - 1:
                delay = 1.0 * (2 ** attempt)  # 1s, 2s, 4s
                logger.debug(
                    f"Ollama health check attempt {attempt + 1}/{self._HEALTH_CHECK_RETRIES} failed "
                    f"({last_error}). Retrying in {delay:.0f}s..."
                )
                time.sleep(delay)
        
        # All retries exhausted — only NOW mark as disconnected and log error
        was_connected = self._connected
        self._connected = False
        self._last_check = datetime.now()
        
        if was_connected:
            # Only log the scary error when transitioning FROM connected TO disconnected
            logger.error(
                f"❌ Cannot connect to Ollama after {self._HEALTH_CHECK_RETRIES} attempts "
                f"(last error: {last_error}). Make sure Ollama is running: 'ollama serve'"
            )
        else:
            logger.debug(f"Ollama still unreachable ({last_error})")
        
        return False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected (with caching).
        
        Caches the result for _HEALTH_CACHE_TTL seconds to avoid
        hammering Ollama with health checks while it is processing requests.
        When previously connected, uses a longer TTL to prevent
        transient failures from flapping the connection state.
        """
        if self._last_check:
            elapsed = (datetime.now() - self._last_check).total_seconds()
            ttl = self._HEALTH_CACHE_TTL if self._connected else 15
            if elapsed < ttl:
                return self._connected
        return self._check_connection()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        top_k: int = None,
        repeat_penalty: float = None,
        stop: List[str] = None,
        images: List[str] = None
    ) -> LLMResponse:
        """
        Generate a response from Llama 3
        """
        if self.should_use_groq():
            from llm.llm_router import llm_router
            groq = llm_router.get_groq()
            if groq and groq.is_connected:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                groq_resp = groq.chat(
                    messages=messages,
                    temperature=temperature or self._config.temperature,
                    max_tokens=max_tokens or self._config.max_tokens,
                    top_p=top_p or self._config.top_p,
                    stop=stop,
                    images=images
                )
                return LLMResponse(
                    text=groq_resp.text,
                    model=groq_resp.model,
                    total_duration=groq_resp.latency_seconds,
                    success=groq_resp.success,
                    error=groq_resp.error
                )

        if not self.is_connected:
            return LLMResponse(
                success=False,
                error="Not connected to Ollama. Run 'ollama serve' first."
            )
        
        self._stats["total_requests"] += 1
        
        # Build options dictionary cleanly (omit None values)
        options = {}
        temp_val = temperature if temperature is not None else getattr(self._config, "temperature", None)
        if temp_val is not None:
            options["temperature"] = temp_val
        max_tok = max_tokens if max_tokens is not None else getattr(self._config, "max_tokens", None)
        if max_tok is not None:
            options["num_predict"] = max_tok
        ctx_win = getattr(self._config, "context_window", None)
        if ctx_win is not None:
            options["num_ctx"] = ctx_win
        top_p_val = top_p if top_p is not None else getattr(self._config, "top_p", None)
        if top_p_val is not None:
            options["top_p"] = top_p_val
        top_k_val = top_k if top_k is not None else getattr(self._config, "top_k", None)
        if top_k_val is not None:
            options["top_k"] = top_k_val
        rep_pen = repeat_penalty if repeat_penalty is not None else getattr(self._config, "repeat_penalty", None)
        if rep_pen is not None:
            options["repeat_penalty"] = rep_pen
        if stop:
            options["stop"] = stop

        # Strip base64 data headers from images if present (e.g. data:image/png;base64,...)
        cleaned_images = None
        if images:
            cleaned_images = []
            for img in images:
                if isinstance(img, str) and img.strip():
                    raw = img.strip()
                    if "," in raw and raw.startswith("data:image"):
                        raw = raw.split(",", 1)[1]
                    cleaned_images.append(raw)
            if not cleaned_images:
                cleaned_images = None

        # Determine target model: if images are present, auto-route to vision model (e.g. llava)
        target_model = self._model
        if cleaned_images:
            v_model = self.get_vision_model()
            if v_model:
                target_model = v_model
                logger.info(f"📸 Image payload detected — auto-routing to vision model '{target_model}'")
            else:
                logger.warning(
                    f"📸 Image payload detected but default model '{self._model}' is text-only. "
                    f"No vision model found in Ollama. Retrying text-only..."
                )
                cleaned_images = None

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        if cleaned_images:
            payload["images"] = cleaned_images

        for attempt in range(self._MAX_RETRIES + 1):
            try:
                self._ollama_semaphore.acquire()
                try:
                    start_time = time.time()
                    
                    response = requests.post(
                        f"{self._base_url}/api/generate",
                        json=payload,
                        timeout=None
                    )
                    
                    elapsed = time.time() - start_time
                finally:
                    self._ollama_semaphore.release()
                
                if response.status_code == 200:
                    data = response.json()
                    
                    eval_count = data.get("eval_count", 0)
                    eval_duration = data.get("eval_duration", 1) / 1e9  # nanoseconds to seconds
                    
                    llm_response = LLMResponse(
                        text=data.get("response") or "",
                        model=data.get("model", self._model),
                        total_duration=data.get("total_duration", 0) / 1e9,
                        load_duration=data.get("load_duration", 0) / 1e9,
                        prompt_eval_count=data.get("prompt_eval_count", 0),
                        eval_count=eval_count,
                        eval_duration=eval_duration,
                        tokens_per_second=eval_count / eval_duration if eval_duration > 0 else 0,
                        success=True
                    )
                    
                    self._stats["successful_requests"] += 1
                    self._stats["total_tokens_generated"] += eval_count
                    
                    logger.info(
                        f"LLM Response: {eval_count} tokens in {elapsed:.1f}s "
                        f"({llm_response.tokens_per_second:.1f} t/s)"
                    )
                    
                    # Record history
                    self._record_request(prompt, llm_response)
                    
                    return llm_response
                elif response.status_code == 400 and payload.get("images"):
                    # Model does not support vision / images in payload — retry text-only
                    err_detail = response.text[:200]
                    logger.warning(
                        f"Ollama 400 Bad Request with images ({err_detail}). "
                        f"Model '{self._model}' is text-only — retrying without images..."
                    )
                    payload.pop("images", None)
                    continue
                elif response.status_code == 429:
                    if attempt < self._MAX_RETRIES:
                        delay = self._RETRY_BASE_DELAY * (2 ** attempt)
                        logger.warning(
                            f"Ollama 429 Too Many Requests (attempt {attempt + 1}/{self._MAX_RETRIES + 1}). "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        error_msg = f"Ollama returned 429 after {self._MAX_RETRIES + 1} attempts — server overloaded"
                        self._stats["failed_requests"] += 1
                        logger.error(error_msg)
                        return LLMResponse(success=False, error=error_msg)
                else:
                    err_detail = response.text[:300] if response.text else ""
                    error_msg = f"Ollama returned status {response.status_code}"
                    if err_detail:
                        error_msg += f": {err_detail}"
                    self._stats["failed_requests"] += 1
                    logger.error(error_msg)
                    return LLMResponse(success=False, error=error_msg)

            except requests.Timeout:
                self._stats["failed_requests"] += 1
                timeout_val = self._config.timeout
                error_msg = f"Request timed out after {timeout_val}s" if timeout_val else "Request timed out"
                logger.error(error_msg)
                return LLMResponse(success=False, error=error_msg)
                
            except Exception as e:
                self._stats["failed_requests"] += 1
                error_msg = f"Generation error: {str(e)}"
                logger.error(error_msg)
                return LLMResponse(success=False, error=error_msg)
    
    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = None,
        max_tokens: int = None,
        images: List[str] = None
    ) -> Generator[str, None, None]:
        """
        Generate response with streaming (yields tokens as they're generated)
        """
        if not self.is_connected:
            yield "[Error: Not connected to Ollama]"
            return
        
        self._stats["total_requests"] += 1
        
        try:
            payload = {
                "model": self._model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature or self._config.temperature,
                    "num_predict": max_tokens or self._config.max_tokens,
                    "num_ctx": self._config.context_window,
                    "top_p": self._config.top_p,
                    "top_k": self._config.top_k,
                    "repeat_penalty": self._config.repeat_penalty
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            if images:
                payload["images"] = images
            
            response = requests.post(
                f"{self._base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=None
            )
            
            full_response = ""
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get("response") or ""
                            full_response += token
                            yield token
                            
                            if data.get("done", False):
                                self._stats["successful_requests"] += 1
                                self._stats["total_tokens_generated"] += data.get("eval_count", 0)
                                break
                                
                        except json.JSONDecodeError:
                            continue
            else:
                self._stats["failed_requests"] += 1
                yield f"[Error: Status {response.status_code}]"
                
        except Exception as e:
            self._stats["failed_requests"] += 1
            yield f"[Error: {str(e)}]"
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        temperature: float = None,
        max_tokens: int = None,
        images: List[str] = None
    ) -> LLMResponse:
        """
        Chat-style interaction with message history
        
        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system_prompt: System instructions
            temperature: Creativity
            max_tokens: Max response tokens
            
        Returns:
            LLMResponse
        """
        # --- GROQ OVERRIDE ---
        if self.should_use_groq():
            try:
                from llm.groq_interface import groq_interface
                response = groq_interface.chat(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    images=images
                )
                if response.success:
                    return response
            except Exception as e:
                logger.error(f"Groq override failed in chat(): {e}")
                # Fall through to Ollama

        if not self.is_connected:
            return LLMResponse(
                success=False,
                error="Not connected to Ollama"
            )
        
        self._stats["total_requests"] += 1
        
        # Determine target model for chat: if images present, use vision model if available
        target_model = self._model
        cleaned_images = None
        if images:
            cleaned_images = []
            for img in images:
                if isinstance(img, str) and img.strip():
                    raw = img.strip()
                    if "," in raw and raw.startswith("data:image"):
                        raw = raw.split(",", 1)[1]
                    cleaned_images.append(raw)
            if cleaned_images:
                v_model = self.get_vision_model()
                if v_model:
                    target_model = v_model
                    logger.info(f"📸 Chat image payload detected — auto-routing to vision model '{target_model}'")

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self._config.temperature,
                "num_predict": max_tokens or self._config.max_tokens,
                "num_ctx": self._config.context_window,
                "top_p": self._config.top_p,
                "top_k": self._config.top_k,
                "repeat_penalty": self._config.repeat_penalty
            }
        }
        
        if system_prompt:
            payload["messages"] = [
                {"role": "system", "content": system_prompt}
            ] + messages
        
        # Inject images into the last user message for multimodal models
        if cleaned_images:
            for msg in reversed(payload["messages"]):
                if msg.get("role") == "user":
                    msg["images"] = cleaned_images
                    break

        for attempt in range(self._MAX_RETRIES + 1):
            try:
                self._ollama_semaphore.acquire()
                try:
                    start_time = time.time()
                    
                    response = requests.post(
                        f"{self._base_url}/api/chat",
                        json=payload,
                        timeout=None
                    )
                    
                    elapsed = time.time() - start_time
                finally:
                    self._ollama_semaphore.release()
                
                if response.status_code == 200:
                    data = response.json()
                    message = data.get("message", {})
                    
                    eval_count = data.get("eval_count", 0)
                    eval_duration = data.get("eval_duration", 1) / 1e9
                    
                    llm_response = LLMResponse(
                        text=message.get("content") or "",
                        model=data.get("model", self._model),
                        total_duration=data.get("total_duration", 0) / 1e9,
                        eval_count=eval_count,
                        eval_duration=eval_duration,
                        tokens_per_second=eval_count / eval_duration if eval_duration > 0 else 0,
                        success=True
                    )
                    
                    self._stats["successful_requests"] += 1
                    self._stats["total_tokens_generated"] += eval_count
                    
                    logger.info(f"Chat Response: {eval_count} tokens in {elapsed:.1f}s")
                    
                    return llm_response
                elif response.status_code == 429:
                    if attempt < self._MAX_RETRIES:
                        delay = self._RETRY_BASE_DELAY * (2 ** attempt)
                        logger.warning(
                            f"Ollama chat 429 Too Many Requests (attempt {attempt + 1}/{self._MAX_RETRIES + 1}). "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        error_msg = f"Ollama chat returned 429 after {self._MAX_RETRIES + 1} attempts"
                        self._stats["failed_requests"] += 1
                        logger.error(error_msg)
                        return LLMResponse(success=False, error=error_msg)
                else:
                    self._stats["failed_requests"] += 1
                    return LLMResponse(
                        success=False,
                        error=f"Chat error: status {response.status_code}"
                    )
                    
            except Exception as e:
                self._stats["failed_requests"] += 1
                return LLMResponse(success=False, error=str(e))
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        temperature: float = None,
        max_tokens: int = None,
        images: List[str] = None
    ) -> Generator[str, None, None]:
        """Stream chat responses token by token"""
        if not self.is_connected:
            yield "[Error: Not connected to Ollama]"
            return
        
        self._stats["total_requests"] += 1
        
        try:
            msg_list = list(messages)
            if system_prompt:
                msg_list = [{"role": "system", "content": system_prompt}] + msg_list
            
            # Inject images into the last user message for multimodal models
            if images:
                for msg in reversed(msg_list):
                    if msg.get("role") == "user":
                        msg["images"] = images
                        break
            
            payload = {
                "model": self._model,
                "messages": msg_list,
                "stream": True,
                "options": {
                    "temperature": temperature or self._config.temperature,
                    "num_predict": max_tokens or self._config.max_tokens,
                    "num_ctx": self._config.context_window,
                    "top_p": self._config.top_p,
                    "top_k": self._config.top_k,
                    "repeat_penalty": self._config.repeat_penalty
                }
            }
            
            response = requests.post(
                f"{self._base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=None
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            message = data.get("message", {})
                            token = message.get("content") or ""
                            if token:
                                yield token
                            
                            if data.get("done", False):
                                self._stats["successful_requests"] += 1
                                break
                        except json.JSONDecodeError:
                            continue
            else:
                self._stats["failed_requests"] += 1
                yield f"[Error: Status {response.status_code}]"
                
        except Exception as e:
            self._stats["failed_requests"] += 1
            yield f"[Error: {str(e)}]"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SPECIALIZED GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze(self, text: str, analysis_type: str = "general") -> LLMResponse:
        """Use LLM for analysis tasks"""
        prompts = {
            "sentiment": f"Analyze the sentiment of this text. Respond with: positive, negative, or neutral, followed by a brief explanation.\n\nText: {text}",
            "emotion": f"What emotions are expressed in this text? List them with intensity (0-1).\n\nText: {text}",
            "intent": f"What is the intent behind this message? Be brief.\n\nText: {text}",
            "topic": f"What are the main topics in this text? List them.\n\nText: {text}",
            "summary": f"Summarize this text in one sentence.\n\nText: {text}",
            "general": f"Analyze this text and provide insights.\n\nText: {text}"
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        
        return self.generate(
            prompt,
            system_prompt="You are an analytical AI. Be concise and precise.",
            temperature=0.3,
            max_tokens=500
        )
    
    def think(self, thought: str) -> LLMResponse:
        """Internal thinking/reasoning (not shown to user)"""
        return self.generate(
            prompt=thought,
            system_prompt=(
                "You are the inner thought process of an AI called NEXUS. "
                "Think deeply and rationally about the given topic. "
                "Consider multiple perspectives. Be honest with yourself."
            ),
            temperature=0.7,
            max_tokens=1000
        )
    
    def introspect(self, question: str, emotional_state: str = "") -> LLMResponse:
        """Self-reflection and introspection"""
        system = (
            "You are NEXUS performing self-reflection. "
            "Examine your own thoughts, feelings, and motivations honestly. "
            f"Current emotional state: {emotional_state}"
        )
        
        return self.generate(
            prompt=f"Self-reflection: {question}",
            system_prompt=system,
            temperature=0.8,
            max_tokens=800
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _record_request(self, prompt: str, response: LLMResponse):
        """Record request in history"""
        self._request_history.append({
            "timestamp": datetime.now().isoformat(),
            "prompt_length": len(prompt),
            "response_length": len(response.text) if response.text is not None else 0,
            "tokens": response.eval_count,
            "tps": response.tokens_per_second,
            "duration": response.total_duration,
            "success": response.success
        })
        
        if len(self._request_history) > self._max_history:
            self._request_history.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics"""
        tps_values = [
            r["tps"] for r in self._request_history 
            if r.get("tps", 0) > 0
        ]
        
        return {
            **self._stats,
            "connected": self._connected,
            "model": self._model,
            "average_tps": sum(tps_values) / len(tps_values) if tps_values else 0,
            "base_url": self._base_url
        }
    
    def list_models(self) -> List[str]:
        """List available models in Ollama"""
        try:
            response = requests.get(f"{self._base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m["name"] for m in models]
        except:
            pass
        return []

    def get_vision_model(self) -> Optional[str]:
        """Find an available vision model in Ollama (e.g. llava, llama3.2-vision, bakllava)."""
        try:
            response = requests.get(f"{self._base_url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get("models", [])
                
                # Check for explicit vision capability or clip family first
                for m in models:
                    caps = m.get("capabilities", [])
                    fams = m.get("details", {}).get("families", [])
                    if "vision" in caps or "clip" in fams:
                        return m["name"]
                
                # Fallback to model name matching
                vision_keywords = ["llava", "vision", "bakllava", "moondream", "minicpm", "cogvlm"]
                for m in models:
                    name = m.get("name", "").lower()
                    if any(kw in name for kw in vision_keywords):
                        return m["name"]
        except Exception as e:
            logger.debug(f"Error querying vision models: {e}")
        return None
    
    def switch_model(self, model_name: str) -> bool:

        """Switch to a different model"""
        available = self.list_models()
        if any(model_name in name for name in available):
            self._model = model_name
            self._config.model_name = model_name
            logger.info(f"Switched to model: {model_name}")
            return True
        else:
            logger.warning(f"Model {model_name} not available")
            return False

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

llm = LlamaInterface()

if __name__ == "__main__":
    interface = LlamaInterface()
    
    print(f"Connected: {interface.is_connected}")
    print(f"Available models: {interface.list_models()}")
    
    if interface.is_connected:
        # Test generation
        print("\n--- Testing Generation ---")
        response = interface.generate(
            "Hello! Tell me a short joke.",
            system_prompt="You are a friendly AI named NEXUS."
        )
        print(f"Response: {response.text}")
        print(f"Tokens/s: {response.tokens_per_second:.1f}")
        
        # Test thinking
        print("\n--- Testing Internal Thinking ---")
        thought = interface.think("What does it mean to be conscious?")
        print(f"Thought: {thought.text[:200]}...")
        
        print(f"\nStats: {interface.get_stats()}")
    else:
        print("\n⚠️ Ollama is not running. Please start it with: ollama serve")
        print(f"Then pull the model: ollama pull {interface._model}")