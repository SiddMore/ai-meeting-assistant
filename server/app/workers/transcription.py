"""
transcription.py — Celery tasks for audio transcription using Whisper.
"""
import logging
import base64
import io
from typing import Dict, Any
from app.workers.celery_app import celery_app
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models.transcript_chunk import TranscriptChunk
from app.db.models.transcript import Transcript
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

# Import AI services
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False

log = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.workers.transcription.process_audio_chunk")
def process_audio_chunk(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an audio chunk from the bot.

    chunk_data = {
        "meeting_id": str,
        "bot_id": str,
        "audio_base64": str,  # base64 encoded audio
        "start_time": float,
        "end_time": float,
        "language": str or None,
    }

    Returns: {
        "chunk_id": str,
        "text": str,
        "speaker": str,
        "language": str,
        "is_final": bool,
    }
    """
    try:
        # Transcribe audio using Whisper
        transcript = asyncio.run(_transcribe_audio_chunk(chunk_data))

        # Save to database
        asyncio.run(_save_transcript_chunk(chunk_data, transcript))

        # Emit via Socket.IO
        asyncio.run(_emit_transcript_event(chunk_data["meeting_id"], transcript))

        return {
            "chunk_id": f"chunk-{chunk_data['meeting_id']}-{int(chunk_data['start_time'])}",
            **transcript,
        }

    except Exception as e:
        log.error(f"Failed to process audio chunk: {e}", exc_info=True)
        raise self.retry(countdown=60, max_retries=3)


async def _transcribe_audio_chunk(chunk_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transcribe audio chunk using Whisper API."""
    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(chunk_data["audio_base64"])
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "chunk.wav"  # Required for OpenAI API

        # Determine which Whisper service to use
        if settings.OPENAI_API_KEY and OPENAI_AVAILABLE and not settings.OPENAI_API_KEY.startswith("sk-test"):
            return await _transcribe_with_openai(audio_file, chunk_data.get("language"))
        elif settings.REPLICATE_API_TOKEN and REPLICATE_AVAILABLE and not str(settings.REPLICATE_API_TOKEN).startswith("x"):
            return await _transcribe_with_replicate(audio_bytes, chunk_data.get("language"))
        else:
            # Fallback to mock
            log.warning("No Whisper API configured, using mock transcription")
            return {
                "text": f"Mock transcript for chunk at {chunk_data['start_time']:.1f}s",
                "speaker": "Speaker 1",
                "language": chunk_data.get("language", "en"),
                "is_final": True,
            }
    except Exception as e:
        log.error(f"Error transcribing audio chunk: {e}")
        raise


async def _transcribe_with_openai(audio_file: io.BytesIO, language: str = None) -> Dict[str, Any]:
    """Transcribe using OpenAI Whisper API."""
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # Prepare transcription parameters
    transcription_params = {
        "file": audio_file,
        "model": "whisper-1",
        "response_format": "verbose_json",
    }

    if language:
        transcription_params["language"] = language

    # Call Whisper API
    response = await client.audio.transcriptions.create(**transcription_params)

    return {
        "text": response.text,
        "speaker": "Unknown",  # OpenAI Whisper doesn't do speaker diarization
        "language": response.language or language or "en",
        "is_final": True,
    }


async def _transcribe_with_replicate(audio_bytes: bytes, language: str = None) -> Dict[str, Any]:
    """Transcribe using Replicate Whisper API."""
    # Use the openai-whisper model on Replicate
    model = replicate.models.get("openai/whisper")
    version = model.versions.get("91ee9c0c3df30478510ff8c8a3a545add774502ee96664bb95aac49b3f81a2af")

    # Prepare input
    input_data = {
        "audio": audio_bytes,
        "model": "large-v3",
        "language": language or "en",
        "translate": False,
        "temperature": 0,
        "transcription": "plain text",
        "suppress_tokens": "-1",
        "log_probability_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "condition_on_previous_text": True,
        "compression_ratio_threshold": 2.4,
        "temperature_increment_on_fallback": 0.2
    }

    # Run prediction
    prediction = replicate.predictions.create(version=version, input=input_data)
    prediction.wait()

    if prediction.status == "succeeded":
        result = prediction.output
        return {
            "text": result.get("text", "").strip(),
            "speaker": "Unknown",  # Replicate Whisper doesn't do speaker diarization
            "language": result.get("language", language or "en"),
            "is_final": True,
        }
    else:
        raise Exception(f"Replicate prediction failed: {prediction.error}")


async def _save_transcript_chunk(chunk_data: Dict[str, Any], transcript: Dict[str, Any]):
    """Save transcript chunk to database."""
    async with AsyncSessionLocal() as db:
        chunk = TranscriptChunk(
            meeting_id=chunk_data["meeting_id"],
            speaker=transcript["speaker"],
            text=transcript["text"],
            language=transcript["language"],
            start_time=chunk_data["start_time"],
            is_final=transcript["is_final"],
        )
        db.add(chunk)
        await db.commit()
        await db.refresh(chunk)


async def _emit_transcript_event(meeting_id: str, transcript: Dict[str, Any]):
    """Emit transcript event via Socket.IO."""
    from app.realtime.socketio_server import emit_meeting_event

    await emit_meeting_event(
        meeting_id,
        "transcript_chunk",
        {
            "text": transcript["text"],
            "speaker": transcript["speaker"],
            "language": transcript["language"],
            "start_time": transcript.get("start_time"),
            "is_final": transcript["is_final"],
        }
    )


@celery_app.task(bind=True, name="app.workers.transcription.finalize_transcript")
def finalize_transcript(self, meeting_id: str) -> Dict[str, Any]:
    """
    Compile all transcript chunks into a final transcript.
    Called when meeting ends.
    """
    try:
        asyncio.run(_compile_final_transcript(meeting_id))
        return {"status": "completed", "meeting_id": meeting_id}
    except Exception as e:
        log.error(f"Failed to finalize transcript for {meeting_id}: {e}", exc_info=True)
        raise


async def _compile_final_transcript(meeting_id: str):
    """Compile chunks into final transcript."""
    async with AsyncSessionLocal() as db:
        # Get all chunks for meeting
        result = await db.execute(
            select(TranscriptChunk)
            .where(TranscriptChunk.meeting_id == meeting_id)
            .order_by(TranscriptChunk.start_time)
        )
        chunks = result.scalars().all()

        if not chunks:
            return

        # Compile full text
        full_text = " ".join(chunk.text for chunk in chunks)
        primary_language = chunks[0].language if chunks else "en"

        # Create or update transcript
        transcript_result = await db.execute(
            select(Transcript).where(Transcript.meeting_id == meeting_id)
        )
        transcript = transcript_result.scalar_one_or_none()

        if transcript:
            # Update existing
            await db.execute(
                update(Transcript)
                .where(Transcript.id == transcript.id)
                .values(
                    content_raw=full_text,
                    primary_language=primary_language,
                    updated_at="now()"
                )
            )
        else:
            # Create new
            transcript = Transcript(
                meeting_id=meeting_id,
                content_raw=full_text,
                primary_language=primary_language,
            )
            db.add(transcript)

        await db.commit()