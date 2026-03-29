"""
tts.py — Text-to-Speech using Kokoro-82M (local, CPU-optimized)
Converts text → audio bytes (WAV) for streaming playback.
Falls back to pyttsx3 if kokoro not available.
"""

import io
import time
import re

# --- Attempt Kokoro first (best quality/speed for local CPU) ---
try:
    from kokoro import KPipeline
    import numpy as np
    import soundfile as sf
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False

# --- Fallback: pyttsx3 ---
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

_kokoro_pipeline = None

def _get_kokoro():
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        # 'a' = American English, lightweight CPU model
        _kokoro_pipeline = KPipeline(lang_code='a')
    return _kokoro_pipeline


def clean_text_for_tts(text: str) -> str:
    # Remove emojis
    emoji_pattern = re.compile(
        "[" 
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F9FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)

    # Fix prices — $28 → 28 dollars
    text = re.sub(r'\$(\d+\.\d+)', lambda m: m.group(1) + ' dollars', text)
    text = re.sub(r'\$(\d+)', lambda m: m.group(1) + ' dollars', text)

    # Fix order IDs — ABC123 → spell naturally, not letter by letter
    text = re.sub(r'\b([A-Z]{2,6}\d{2,6})\b', lambda m: ' '.join(m.group(1)), text)

    # Remove markdown
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'_+', '', text)
    text = re.sub(r'#+\s*', '', text)

    # Fix pipe separators
    text = text.replace(' | ', ', ')
    text = text.replace('|', ', ')

    # Fix parentheses with prices — (28 dollars) → for 28 dollars
    text = re.sub(r'\((\d+ dollars)\)', r'for \1', text)

    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def synthesize(text: str) -> dict:
    """
    Convert text to speech audio.
    Returns: {audio_bytes (WAV), sample_rate, latency, engine}
    """
    text = clean_text_for_tts(text)
    if not text:
        return {"error": "Empty text after cleaning", "audio_bytes": b""}

    # Truncate very long responses for TTS (read first ~400 chars)
    if len(text) > 500:
        # Find a sentence boundary
        trunc = text[:500]
        last_period = max(trunc.rfind('.'), trunc.rfind('!'), trunc.rfind('?'))
        if last_period > 200:
            text = trunc[:last_period + 1] + " ..."
        else:
            text = trunc + " ..."

    start = time.time()

    # --- Try Kokoro ---
    if KOKORO_AVAILABLE:
        try:
            pipeline = _get_kokoro()
            audio_chunks = []
            sample_rate = 24000  # Kokoro default

            for _, _, audio in pipeline(text, voice='af_heart', speed=1.1):
                audio_chunks.append(audio)

            if audio_chunks:
                import numpy as np
                combined = np.concatenate(audio_chunks)

                # Encode to WAV bytes
                buf = io.BytesIO()
                sf.write(buf, combined, sample_rate, format='WAV', subtype='PCM_16')
                buf.seek(0)
                wav_bytes = buf.read()

                return {
                    "audio_bytes": wav_bytes,
                    "sample_rate": sample_rate,
                    "latency": round(time.time() - start, 3),
                    "engine": "kokoro"
                }
        except Exception as e:
            pass  # Fall through to next engine

    # --- Fallback: pyttsx3 ---
    if PYTTSX3_AVAILABLE:
        try:
            import tempfile, os
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)   # Slightly faster than default
            engine.setProperty('volume', 0.9)

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name

            engine.save_to_file(text, tmp_path)
            engine.runAndWait()

            with open(tmp_path, 'rb') as f:
                wav_bytes = f.read()

            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            return {
                "audio_bytes": wav_bytes,
                "sample_rate": 22050,
                "latency": round(time.time() - start, 3),
                "engine": "pyttsx3"
            }
        except Exception as e:
            return {"error": str(e), "audio_bytes": b""}

    return {"error": "No TTS engine available. Install kokoro or pyttsx3.", "audio_bytes": b""}


def check_health() -> dict:
    """Return which TTS engines are available."""
    return {
        "kokoro": KOKORO_AVAILABLE,
        "pyttsx3": PYTTSX3_AVAILABLE,
        "any": KOKORO_AVAILABLE or PYTTSX3_AVAILABLE
    }
