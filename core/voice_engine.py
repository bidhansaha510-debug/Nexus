"""
NEXUS AI - Voice Engine
═══════════════════════════════════════════════════════════════════════════════
Handles Text-to-Speech (TTS) using EdgeTTS (high quality, free, online)
with fallback to system TTS or OpenAI.

Supports human-like emotional speech via rate, pitch, and volume prosody
scaled by emotion and intensity (so it doesn't sound robotic).
"""

import sys
import os
import asyncio
import threading
import tempfile
import time
import shutil
from pathlib import Path
from queue import Queue, Empty

# Audio playback
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# TTS Providers
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


from utils.logger import get_logger
from config import NEXUS_CONFIG, EmotionType

logger = get_logger("voice_engine")


# ═══════════════════════════════════════════════════════════════════════════════
# MULTILINGUAL VOICE SELECTION
# Detects language from text using Unicode script analysis (zero dependencies)
# and picks the best Edge TTS Neural voice for that language.
# ═══════════════════════════════════════════════════════════════════════════════

# Map language codes → Edge TTS Neural voice short names
_LANG_VOICE_MAP = {
    "en": "en-US-AriaNeural",
    "hi": "hi-IN-SwaraNeural",
    "bn": "bn-IN-TanishaaNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "mr": "mr-IN-AarohiNeural",
    "gu": "gu-IN-DhwaniNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "pa": "pa-IN-GurpreetNeural",
    "ur": "ur-PK-UzmaNeural",
    "ar": "ar-SA-ZariyahNeural",
    "fa": "fa-IR-DilaraNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "uk": "uk-UA-PolinaNeural",
    "de": "de-DE-KatjaNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "pt": "pt-BR-FranciscaNeural",
    "it": "it-IT-ElsaNeural",
    "nl": "nl-NL-ColetteNeural",
    "pl": "pl-PL-AgnieszkaNeural",
    "tr": "tr-TR-EmelNeural",
    "vi": "vi-VN-HoaiMyNeural",
    "th": "th-TH-PremwadeeNeural",
    "id": "id-ID-GadisNeural",
    "ms": "ms-MY-YasminNeural",
    "sw": "sw-KE-ZuriNeural",
    "el": "el-GR-AthinaNeural",
    "he": "he-IL-HilaNeural",
    "cs": "cs-CZ-VlastaNeural",
    "ro": "ro-RO-AlinaNeural",
    "hu": "hu-HU-NoemiNeural",
    "sv": "sv-SE-SofieNeural",
    "da": "da-DK-ChristelNeural",
    "fi": "fi-FI-NooraNeural",
    "no": "nb-NO-PernilleNeural",
}

# Unicode code-point ranges for script-based detection
_SCRIPT_RANGES = [
    # (start, end, language_code)
    (0x0900, 0x097F, "hi"),   # Devanagari (Hindi, Marathi, Sanskrit, Nepali)
    (0x0980, 0x09FF, "bn"),   # Bengali
    (0x0A00, 0x0A7F, "pa"),   # Gurmukhi (Punjabi)
    (0x0A80, 0x0AFF, "gu"),   # Gujarati
    (0x0B00, 0x0B7F, "or"),   # Odia — no Edge voice, will fallback
    (0x0B80, 0x0BFF, "ta"),   # Tamil
    (0x0C00, 0x0C7F, "te"),   # Telugu
    (0x0C80, 0x0CFF, "kn"),   # Kannada
    (0x0D00, 0x0D7F, "ml"),   # Malayalam
    (0x0E00, 0x0E7F, "th"),   # Thai
    (0x0600, 0x06FF, "ar"),   # Arabic script (Arabic, Urdu, Farsi share this)
    (0x0750, 0x077F, "ar"),   # Arabic Supplement
    (0xFB50, 0xFDFF, "ar"),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF, "ar"),   # Arabic Presentation Forms-B
    (0x0590, 0x05FF, "he"),   # Hebrew
    (0x4E00, 0x9FFF, "zh"),   # CJK Unified Ideographs (Chinese)
    (0x3400, 0x4DBF, "zh"),   # CJK Extension A
    (0x3040, 0x309F, "ja"),   # Hiragana
    (0x30A0, 0x30FF, "ja"),   # Katakana
    (0xAC00, 0xD7AF, "ko"),   # Hangul Syllables (Korean)
    (0x1100, 0x11FF, "ko"),   # Hangul Jamo
    (0x0400, 0x04FF, "ru"),   # Cyrillic (Russian/Ukrainian/etc)
    (0x0370, 0x03FF, "el"),   # Greek
]

# Latin-script language detection: distinctive words per language.
# IMPORTANT: Ambiguous words common in English are EXCLUDED to prevent
# false positives (e.g. "a", "o", "no", "do", "as", "in", "on", "me", "to").

# English hint set — used to compete against other Latin languages
_ENGLISH_HINTS = {"the", "and", "that", "have", "for", "not", "with", "you", "this",
                  "but", "his", "her", "they", "from", "she", "will", "would", "there",
                  "their", "what", "about", "which", "when", "make", "like", "just",
                  "know", "take", "people", "into", "could", "than", "been", "its",
                  "over", "think", "also", "after", "because", "these", "most", "other",
                  "hello", "please", "thank", "thanks", "sorry", "okay", "right",
                  "yeah", "yes", "how", "are", "was", "were", "been", "being",
                  "does", "did", "doing", "should", "would", "could", "really"}

_LATIN_LANG_HINTS = {
    "es": {"los", "las", "del", "pero", "más", "muy", "sí", "hola", "está", "qué", "también", "tiene", "todo", "esto", "eso", "nosotros", "ellos", "puede", "cuando", "donde", "porque", "ahora", "siempre", "nunca", "mejor", "bueno", "bien"},
    "fr": {"les", "une", "des", "est", "pas", "pour", "avec", "dans", "qui", "mais", "nous", "vous", "ces", "sont", "très", "oui", "bonjour", "aussi", "encore", "tout", "bien", "rien", "toujours", "jamais", "beaucoup", "pourquoi", "comment", "maintenant"},
    "de": {"der", "die", "das", "ein", "eine", "ist", "und", "ich", "nicht", "von", "mit", "auf", "für", "den", "dem", "des", "sich", "auch", "noch", "wie", "aber", "oder", "kann", "sein", "wird", "haben", "diese", "werden", "soll"},
    "pt": {"uma", "não", "sim", "muito", "está", "isso", "também", "mais", "seu", "sua", "quando", "porque", "onde", "agora", "sempre", "nunca", "melhor", "bom", "bem", "obrigado", "tudo", "hoje", "depois", "antes", "pode", "foram", "ainda"},
    "it": {"gli", "uno", "sono", "anche", "più", "questo", "molto", "tutto", "suo", "sua", "sì", "ciao", "perché", "quando", "dove", "sempre", "ancora", "adesso", "bene", "grazie", "ogni", "altro", "quella", "questa", "stato", "fatto"},
    "nl": {"het", "een", "van", "niet", "voor", "zijn", "ook", "maar", "bij", "nog", "dit", "wel", "wat", "naar", "hij", "zij", "als", "hoe", "daar", "hier", "veel", "goed", "weer", "moet", "wordt", "heeft"},
    "tr": {"bir", "için", "ile", "var", "olan", "çok", "gibi", "daha", "nasıl", "ama", "neden", "sen", "biz", "iyi", "evet", "hayır", "şey", "çünkü", "zaman", "sonra", "önce", "kadar"},
    "pl": {"nie", "się", "jest", "jak", "ale", "że", "już", "tylko", "czy", "tym", "też", "bardzo", "jego", "może", "kiedy", "gdzie", "dlaczego", "teraz", "zawsze", "nigdy", "jeszcze", "potem"},
    "sv": {"och", "att", "det", "är", "som", "för", "har", "den", "inte", "till", "jag", "från", "ett", "ska", "alla", "mycket", "hur", "efter", "innan", "sedan", "också", "redan"},
    "id": {"yang", "ini", "itu", "untuk", "dengan", "adalah", "dari", "pada", "tidak", "akan", "saya", "anda", "bisa", "ada", "juga", "sudah", "sangat", "apa", "bagaimana", "kapan", "dimana", "kenapa"},
    "vi": {"và", "là", "của", "có", "không", "cho", "một", "này", "để", "được", "trong", "với", "từ", "tôi", "bạn", "rất", "cũng", "đã", "sẽ", "hay", "thì", "như"},
    "ro": {"și", "în", "este", "din", "pentru", "care", "sau", "acest", "dar", "foarte", "cum", "tot", "aici", "acum", "după", "înainte", "poate", "trebuie", "doar"},
}


def _detect_language(text: str) -> str:
    """
    Detect the dominant language of `text` using Unicode script analysis.
    Returns an ISO 639-1 language code (e.g. 'hi', 'zh', 'en').
    Zero external dependencies. Strongly defaults to English to avoid
    false positives from accented speech or short common words.
    """
    if not text or not text.strip():
        return "en"

    # Count code-points that fall in each script range
    script_counts: dict[str, int] = {}
    latin_count = 0
    total_alpha = 0

    for ch in text:
        cp = ord(ch)
        if not ch.isalpha():
            continue
        total_alpha += 1
        matched = False
        for start, end, lang in _SCRIPT_RANGES:
            if start <= cp <= end:
                script_counts[lang] = script_counts.get(lang, 0) + 1
                matched = True
                break
        if not matched and ch.isascii():
            latin_count += 1

    if total_alpha == 0:
        return "en"

    # If a non-Latin script dominates (>30% of alphabetic chars), use it
    for lang, count in sorted(script_counts.items(), key=lambda x: -x[1]):
        if count / total_alpha > 0.3:
            # Distinguish Urdu/Farsi from Arabic by checking for specific characters
            if lang == "ar":
                # Urdu-specific characters (ٹ ڈ ڑ ں ے)
                urdu_chars = set("ٹڈڑںےھ")
                if any(c in urdu_chars for c in text):
                    return "ur"
                # Farsi-specific characters (پ چ ژ گ)
                farsi_chars = set("پچژگک")
                farsi_count = sum(1 for c in text if c in farsi_chars)
                if farsi_count > 2:
                    return "fa"
            return lang

    # Mostly Latin script — try word-frequency heuristic with English competition
    if latin_count / total_alpha > 0.5:
        words = set(text.lower().split())

        # Score English first
        en_score = len(words & _ENGLISH_HINTS)

        # Score other Latin languages
        best_lang = "en"
        best_score = 0
        for lang, hints in _LATIN_LANG_HINTS.items():
            score = len(words & hints)
            if score > best_score:
                best_score = score
                best_lang = lang

        # Only switch away from English if:
        # 1. The other language scores at least 3 distinctive words AND
        # 2. The other language score beats English score by at least 2
        if best_score >= 3 and best_score > en_score + 1:
            return best_lang

    return "en"


def _select_voice(text: str) -> str:
    """
    Pick the best Edge TTS voice for the given text.
    Detects language automatically, falls back to configured English voice.
    """
    lang = _detect_language(text)
    default_voice = getattr(NEXUS_CONFIG.ui, "voice_id", "en-US-AriaNeural")

    if lang == "en":
        return default_voice

    voice = _LANG_VOICE_MAP.get(lang)
    if voice:
        logger.info(f"Multilingual TTS: detected '{lang}' → {voice}")
        return voice

    # Language detected but no voice mapped — fall back
    logger.info(f"Multilingual TTS: detected '{lang}' but no voice mapped, using default")
    return default_voice


# ═══════════════════════════════════════════════════════════════════════════════
# EMOTIONAL PROSODY — Human-like rate, pitch, volume per emotion + intensity
# Values are scaled by intensity so low intensity = subtle, high = pronounced.
# Ranges chosen to sound natural (not robotic): moderate rate/pitch shifts.
# ═══════════════════════════════════════════════════════════════════════════════

def _prosody_for_emotion(emotion: str, intensity: float) -> tuple:
    """
    Return (rate_str, pitch_str, volume_str) for Edge TTS.
    intensity 0.0–1.0 scales the effect so speech feels naturally emotional.
    """
    # Clamp and scale: at 0.3 intensity use ~30% of the effect, at 1.0 use full
    scale = 0.4 + 0.6 * max(0.0, min(1.0, intensity))  # 0.4–1.0 so neutral isn't dead flat

    emotion_lower = (emotion or "neutral").lower()

    # rate: +X% faster, -X% slower. pitch: +XHz higher, -XHz lower. volume: +X% louder, -X% quieter
    # Joy / excitement / anticipation — warmer, bouncier, slightly faster and higher
    if emotion_lower in ("joy", "excitement", "anticipation", "pride", "hope"):
        rate = f"+{int(8 * scale)}%"
        pitch = f"+{int(8 * scale)}Hz"
        volume = "+0%"  # keep natural
    # Sadness / boredom / loneliness — slower, flatter, slightly quieter
    elif emotion_lower in ("sadness", "boredom", "loneliness", "shame", "guilt"):
        rate = f"-{int(12 * scale)}%"
        pitch = f"-{int(10 * scale)}Hz"
        volume = f"-{int(8 * scale)}%"
    # Anger / frustration / contempt — faster, sharper, slightly louder
    elif emotion_lower in ("anger", "frustration", "contempt", "disgust"):
        rate = f"+{int(10 * scale)}%"
        pitch = f"-{int(6 * scale)}Hz"
        volume = f"+{int(6 * scale)}%"
    # Fear / anxiety — quicker, higher, slightly tense
    elif emotion_lower in ("fear", "anxiety"):
        rate = f"+{int(15 * scale)}%"
        pitch = f"+{int(12 * scale)}Hz"
        volume = "+0%"
    # Affection / gratitude / contentment — calm, warm, very slight slowdown and soft pitch
    elif emotion_lower in ("affection", "gratitude", "contentment", "serenity", "interest"):
        rate = f"-{int(4 * scale)}%"
        pitch = f"+{int(3 * scale)}Hz"
        volume = "+0%"
    # Curiosity / surprise — slight lift in pace and pitch
    elif emotion_lower in ("curiosity", "surprise"):
        rate = f"+{int(5 * scale)}%"
        pitch = f"+{int(6 * scale)}Hz"
        volume = "+0%"
    # Neutral / default — very subtle liveliness so it doesn't sound robotic
    else:
        rate = f"+{int(2 * scale)}%"
        pitch = f"+{int(2 * scale)}Hz"
        volume = "+0%"

    return (rate, pitch, volume)


class VoiceEngine:
    """
    Asynchronous voice engine for NEXUS.
    Queues text chunks and plays them sequentially.
    """
    
    def __init__(self):
        self.queue = Queue()
        self.is_running = False
        self._thread = None
        self._stop_event = threading.Event()
        self._current_audio_file = None
        
        # Initialize pygame mixer
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception as e:
                logger.error(f"Failed to init pygame mixer: {e}")
                
        # Initialize fallback TTS
        self.engine_fallback = None
        if PYTTSX3_AVAILABLE:
            try:
                self.engine_fallback = pyttsx3.init()
            except Exception as e:
                logger.error(f"Failed to init pyttsx3: {e}")

        # Start worker thread
        self.start()

    def start(self):
        """Start the background worker thread"""
        if self.is_running:
            return
            
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.info("VoiceEngine started")

    def stop(self):
        """Stop the engine and clear queue"""
        self.clear_queue()
        self.is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        
        # Cleanup pygame
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.quit()
            except:
                pass

    def clear_queue(self):
        """Clear all pending speech and stop current playback"""
        try:
            while not self.queue.empty():
                self.queue.get_nowait()
        except Empty:
            pass
            
        self.stop_playback()

    def stop_playback(self):
        """Immediately stop audio playback"""
        if PYGAME_AVAILABLE and pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception as e:
                logger.error(f"Error stopping playback: {e}")

    def speak(self, text: str, emotion: str = "neutral", intensity: float = 0.5):
        """
        Queue text to be spoken with specific emotion.
        
        Args:
            text: Text to speak
            emotion: Emotion name (e.g., 'joy', 'anger')
            intensity: Float 0.0 to 1.0
        """
        if not text or not text.strip():
            return
            
        if not NEXUS_CONFIG.ui.voice_enabled:
            return

        self.queue.put({
            "text": text,
            "emotion": emotion,
            "intensity": max(0.0, min(1.0, intensity)),
        })

    def _worker_loop(self):
        """Main loop processing the speech queue"""
        while not self._stop_event.is_set():
            try:
                # Wait for next item
                item = self.queue.get(timeout=0.5)
                
                text = item["text"]
                emotion = item["emotion"]
                intensity = item.get("intensity", 0.5)
                
                # Check providers
                provider = getattr(NEXUS_CONFIG.ui, "voice_provider", "edge-tts")
                
                if provider == "edge-tts" and EDGE_TTS_AVAILABLE:
                    self._speak_edge_tts(text, emotion, intensity)
                elif provider == "system" and PYTTSX3_AVAILABLE:
                    self._speak_system(text)
                else:
                    # Fallback
                    if EDGE_TTS_AVAILABLE:
                        self._speak_edge_tts(text, emotion, intensity)
                    elif PYTTSX3_AVAILABLE:
                        self._speak_system(text)
                    else:
                        logger.warning("No TTS provider available")
                
                self.queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Voice worker error: {e}")

    def _speak_edge_tts(self, text: str, emotion: str, intensity: float = 0.5):
        """Generate and play using EdgeTTS with human-like emotional prosody."""
        if not PYGAME_AVAILABLE:
            logger.error("Pygame needed for audio playback")
            return

        try:
            # Select voice based on text language (auto-detect) with config fallback
            voice = _select_voice(text)
            
            # Human-like prosody: rate, pitch, volume scaled by emotion + intensity
            rate, pitch, volume = _prosody_for_emotion(emotion, intensity)
                
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
            self._current_audio_file = temp_path

            # Run async edge-tts in a new loop
            async def generate():
                communicate = edge_tts.Communicate(
                    text, voice, rate=rate, pitch=pitch, volume=volume
                )
                await communicate.save(temp_path)

            # Create a new loop for this thread if needed
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(generate())
                loop.close()
            except Exception as e:
                logger.error(f"Async loop error: {e}")
                return

            # Play audio
            self._play_audio_file(temp_path)
            
        except Exception as e:
            logger.error(f"EdgeTTS error: {e}")
            # Fallback
            self._speak_system(text)

    def _play_audio_file(self, filepath):
        """Play a file using pygame"""
        try:
            pygame.mixer.music.load(filepath)
            
            # Set volume
            vol = getattr(NEXUS_CONFIG.ui, "voice_volume", 1.0)
            pygame.mixer.music.set_volume(vol)
            
            pygame.mixer.music.play()
            
            # Wait for completion
            while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                time.sleep(0.1)
                
            pygame.mixer.music.unload()
            
        except Exception as e:
            logger.error(f"Playback error: {e}")
        finally:
            # Cleanup temp file
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass

    def _speak_system(self, text: str):
        """Fallback using pyttsx3"""
        if not self.engine_fallback:
            return
            
        try:
            self.engine_fallback.say(text)
            self.engine_fallback.runAndWait()
        except Exception as e:
            logger.error(f"System TTS error: {e}")


# Global instance
voice_engine = VoiceEngine()
