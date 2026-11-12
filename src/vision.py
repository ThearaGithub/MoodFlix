"""Optional webcam mood detection.

This module is deliberately optional. The core app must run with nothing but
the dependencies in ``requirements.txt``; installing
``requirements-vision.txt`` enables the camera path.

``suggest_mood()`` takes the JPEG bytes from ``st.camera_input``, runs a
pre-trained facial-expression classifier (DeepFace, which ships small CNN
weights and downloads them once), and maps the detected emotion onto one of
the eight MoodFlix moods.

Privacy: the captured frame is written to a temporary file only because
DeepFace accepts a path, and that file is deleted in a ``finally`` block.
Nothing is uploaded, cached, or attached to the session.
"""

from __future__ import annotations

import functools
import importlib.util
import os
import tempfile

# Emotions the classifier reports, mapped onto the moods the app offers.
# Romantic and Nostalgic have no facial expression, so they stay manual.
EMOTION_TO_MOOD = {
    "happy": "Happy",
    "surprise": "Excited",
    "angry": "Excited",
    "fear": "Scared",
    "disgust": "Thoughtful",
    "sad": "Sad",
    "neutral": "Relaxed",
}

EMOTION_EMOJI = {
    "happy": "😄",
    "surprise": "😲",
    "angry": "😠",
    "fear": "😨",
    "disgust": "😖",
    "sad": "😢",
    "neutral": "😐",
}

# Moods the camera can never suggest: a face carries no "romantic" or
# "nostalgic" signal. The other six are reachable (disgust maps to
# Thoughtful, anger and surprise both map to Excited).
CAMERA_MOODS = sorted(set(EMOTION_TO_MOOD.values()))
MANUAL_ONLY_MOODS = ["Romantic", "Nostalgic"]

INSTALL_HINT = (
    "Camera mood detection needs the optional extras. Run "
    "`pip install -r requirements-vision.txt` and restart the app."
)


class VisionUnavailable(RuntimeError):
    """Raised when the optional vision dependencies are not installed."""


class VisionError(RuntimeError):
    """Raised when a photo could not be analysed."""


@functools.lru_cache(maxsize=1)
def is_available() -> bool:
    """True when the optional vision dependencies are installed.

    Uses ``find_spec`` rather than importing: TensorFlow takes seconds to
    import and DeepFace imports fine even when TensorFlow is missing, so a
    plain ``import deepface`` would report the extras as available and then
    fail at detection time. The answer is cached for the life of the
    process, so restart the app after installing the extras.
    """
    return all(
        importlib.util.find_spec(name) is not None
        for name in ("deepface", "tensorflow")
    )


def _load_deepface():
    if not is_available():
        raise VisionUnavailable(INSTALL_HINT)
    try:
        from deepface import DeepFace
    except Exception as exc:  # pragma: no cover - depends on environment
        raise VisionUnavailable(INSTALL_HINT) from exc
    return DeepFace


def analyze(image_bytes: bytes) -> list[tuple[str, float]]:
    """Return ``[(emotion, probability), ...]`` sorted by probability."""
    if not image_bytes:
        raise VisionError("The photo was empty. Try again.")

    DeepFace = _load_deepface()
    handle = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    path = handle.name
    try:
        handle.write(image_bytes)
        handle.close()
        result = DeepFace.analyze(
            img_path=path,
            actions=["emotion"],
            detector_backend="opencv",
            enforce_detection=False,
            silent=True,
        )
    except VisionUnavailable:
        raise
    except Exception as exc:
        raise VisionError(
            "Could not analyse that photo. Try better lighting and face the "
            "camera directly."
        ) from exc
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    faces = result if isinstance(result, list) else [result]
    if not faces:
        raise VisionError("No face was found in the photo.")

    scores = dict(faces[0].get("emotion") or {})
    if not scores:
        raise VisionError("No face was found in the photo.")
    ranked = sorted(
        ((str(name).lower(), float(value)) for name, value in scores.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    return ranked


def _as_fraction(value: float) -> float:
    """DeepFace reports percentages; the UI wants 0-1."""
    value = float(value)
    return value / 100.0 if value > 1.0 else value


def suggest_mood(image_bytes: bytes) -> dict:
    """Map a photo onto a MoodFlix mood.

    Returns ``{"emotion", "emoji", "confidence", "mood", "runner_up",
    "scores"}``. ``confidence`` and ``runner_up["confidence"]`` are 0-1;
    ``scores`` keeps DeepFace's percentages for display.
    """
    ranked = analyze(image_bytes)
    emotion, confidence = ranked[0]
    mood = EMOTION_TO_MOOD.get(emotion, "Relaxed")
    runner_up = None
    if len(ranked) > 1:
        second_emotion, second_score = ranked[1]
        second_mood = EMOTION_TO_MOOD.get(second_emotion)
        if second_mood and second_mood != mood:
            runner_up = {
                "emotion": second_emotion,
                "mood": second_mood,
                "confidence": _as_fraction(second_score),
            }
    return {
        "emotion": emotion,
        "emoji": EMOTION_EMOJI.get(emotion, "🙂"),
        "confidence": _as_fraction(confidence),
        "mood": mood,
        "runner_up": runner_up,
        "scores": ranked[:3],
    }
