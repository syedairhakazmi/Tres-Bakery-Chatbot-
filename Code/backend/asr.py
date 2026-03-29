"""
asr.py — Automatic Speech Recognition for Tres Bakery Chatbot
Uses Faster Whisper (base model, English only)
Accepts audio bytes from browser MediaRecorder (WebM/WAV)
"""

import io
import time
import tempfile
import os
from faster_whisper import WhisperModel

# ─────────────────────────────────────────────────────────
# Model config
# ─────────────────────────────────────────────────────────

MODEL_SIZE   = "base"       # tiny | base | small | medium
LANGUAGE     = "en"         # English only
DEVICE       = "cpu"        # use "cuda" if you have a GPU
COMPUTE_TYPE = "int8"       # int8 = fastest on CPU, good accuracy

# Load model once at startup (not on every request)
_model = None

def _get_model ():
    global _model
    if _model is None:
        print (f"[ASR] Loading Faster Whisper model: {MODEL_SIZE} ...")
        _model = WhisperModel (MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        print ("[ASR] Model loaded successfully.")
    return _model


# ─────────────────────────────────────────────────────────
# Main transcription function
# ─────────────────────────────────────────────────────────

def transcribe_audio (audio_bytes: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Takes raw audio bytes from browser (WebM, WAV, OGG, etc.)
    Returns: { text, language, latency, error (if any) }
    """
    if not audio_bytes:
        return {"text": "", "language": "en", "latency": 0, "error": "No audio received"}

    start = time.time ()

    try:
        model = _get_model ()

        # Write audio bytes to a temp file (Faster Whisper needs a file path)
        suffix = _get_suffix (mime_type)
        with tempfile.NamedTemporaryFile (suffix=suffix, delete=False) as tmp:
            tmp.write (audio_bytes)
            tmp_path = tmp.name

        try:
            # Run transcription
            segments, info = model.transcribe (
                tmp_path,
                language          = LANGUAGE,
                beam_size         = 5,
                vad_filter        = True,        # skip silence automatically
                vad_parameters    = {"min_silence_duration_ms": 500},
                condition_on_previous_text = False
            )

            # Collect all segments into one string
            text_parts = []
            for segment in segments:
                cleaned = segment.text.strip ()
                if cleaned:
                    text_parts.append (cleaned)

            full_text = " ".join (text_parts).strip ()

        finally:
            # Always clean up temp file
            os.unlink (tmp_path)

        latency = round (time.time () - start, 3)

        # If Whisper returns empty, handle gracefully
        if not full_text:
            return {
                "text"    : "",
                "language": LANGUAGE,
                "latency" : latency,
                "error"   : "No speech detected"
            }

        return {
            "text"    : full_text,
            "language": info.language or LANGUAGE,
            "latency" : latency
        }

    except Exception as e:
        latency = round (time.time () - start, 3)
        print (f"[ASR] Error during transcription: {e}")
        return {
            "text"    : "",
            "language": LANGUAGE,
            "latency" : latency,
            "error"   : str (e)
        }


# ─────────────────────────────────────────────────────────
# Health check (called by main.py /health endpoint)
# ─────────────────────────────────────────────────────────

def check_health () -> bool:
    """Returns True if the ASR model is loaded and ready."""
    try:
        _get_model ()
        return True
    except Exception as e:
        print (f"[ASR] Health check failed: {e}")
        return False


# ─────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────

def _get_suffix (mime_type: str) -> str:
    """Map MIME type to file extension for temp file."""
    mapping = {
        "audio/webm"      : ".webm",
        "audio/wav"       : ".wav",
        "audio/wave"      : ".wav",
        "audio/ogg"       : ".ogg",
        "audio/mp4"       : ".mp4",
        "audio/mpeg"      : ".mp3",
        "audio/mp3"       : ".mp3",
        "audio/x-wav"     : ".wav",
        "audio/x-m4a"     : ".m4a",
    }
    return mapping.get (mime_type.lower (), ".webm")  # default to webm (browser default)