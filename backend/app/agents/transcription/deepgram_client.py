"""
Deepgram client wrapper for ClinSync.
Handles audio transcription with multilingual support.
"""

import logging
import structlog

# Patch missing log levels that Deepgram SDK expects before importing it
# Deepgram uses verboselogs which adds NOTICE, VERBOSE, SPAM, SUCCESS levels
_EXTRA_LEVELS = {
    "notice": 25,
    "verbose": 15,
    "spam": 5,
    "success": 35,
}
for _level_name, _level_num in _EXTRA_LEVELS.items():
    if not hasattr(logging, _level_name.upper()):
        logging.addLevelName(_level_num, _level_name.upper())
    if not hasattr(logging.Logger, _level_name):
        def _make_method(num):
            def _log_method(self, message, *args, **kwargs):
                if self.isEnabledFor(num):
                    self._log(num, message, args, **kwargs)
            return _log_method
        setattr(logging.Logger, _level_name, _make_method(_level_num))

from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from app.core.config import settings

logger = structlog.get_logger(__name__)


class TranscriptionResult:
    def __init__(
        self,
        transcript: str,
        language: str,
        confidence: float,
        duration_seconds: float,
        words: list[dict],
    ):
        self.transcript = transcript
        self.language = language
        self.confidence = confidence
        self.duration_seconds = duration_seconds
        self.words = words

    def __repr__(self) -> str:
        return (
            f"<TranscriptionResult lang={self.language} "
            f"confidence={self.confidence:.2f} "
            f"duration={self.duration_seconds:.1f}s "
            f"words={len(self.words)}>"
        )


class DeepgramTranscriptionClient:
    """
    Wraps the Deepgram SDK for ClinSync audio transcription.

    Supports:
    - Pre-recorded audio files (mp3, wav, m4a, ogg, flac)
    - Multilingual detection (critical for India — Hindi, Bengali, Tamil, etc.)
    - Medical vocabulary boosting
    - Speaker diarization (who said what)
    """

    MEDICAL_KEYWORDS = [
        "hypertension", "diabetes", "prescription", "diagnosis",
        "symptoms", "medication", "dosage", "milligrams", "tablets",
        "capsules", "blood pressure", "glucose", "cholesterol",
        "echocardiogram", "electrocardiogram", "haemoglobin",
        "creatinine", "bilirubin", "platelets", "leucocytes",
    ]

    def __init__(self):
        self._client = DeepgramClient(api_key=settings.DEEPGRAM_API_KEY)

    async def transcribe_file(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/wav",
        language: str = "en",
        detect_language: bool = True,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file from bytes.

        Args:
            audio_bytes: Raw audio file content
            mime_type: Audio MIME type (audio/wav, audio/mp3, etc.)
            language: Primary language hint (en, hi, ta, bn, etc.)
            detect_language: Auto-detect language (recommended for India)

        Returns:
            TranscriptionResult with transcript and metadata
        """
        logger.info(
            "Starting transcription",
            mime_type=mime_type,
            language=language,
            detect_language=detect_language,
            size_bytes=len(audio_bytes),
        )

        payload: FileSource = {"buffer": audio_bytes, "mimetype": mime_type}

        options = PrerecordedOptions(
            model="nova-2-medical",
            language=language if not detect_language else None,
            detect_language=detect_language,
            punctuate=True,
            diarize=True,
            smart_format=True,
            utterances=True,
            keywords=self.MEDICAL_KEYWORDS,
        )

        response = await self._client.listen.asyncprerecorded.v("1").transcribe_file(
            payload, options
        )

        result = response.results
        channel = result.channels[0].alternatives[0]

        transcript = channel.transcript
        confidence = channel.confidence
        words = [
            {
                "word": w.word,
                "start": w.start,
                "end": w.end,
                "confidence": w.confidence,
                "speaker": getattr(w, "speaker", None),
            }
            for w in (channel.words or [])
        ]

        detected_language = (
            result.channels[0].detected_language
            if detect_language
            else language
        )

        duration = response.metadata.duration if response.metadata else 0.0

        logger.info(
            "Transcription complete",
            language=detected_language,
            confidence=confidence,
            duration=duration,
            word_count=len(words),
        )

        return TranscriptionResult(
            transcript=transcript,
            language=detected_language or language,
            confidence=confidence,
            duration_seconds=duration,
            words=words,
        )


# Singleton
deepgram_client = DeepgramTranscriptionClient()