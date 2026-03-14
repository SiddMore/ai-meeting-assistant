"""
translation.py — Celery tasks for text translation using DeepL or Google Translate.
"""
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from app.workers.celery_app import celery_app
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models.transcript import Transcript
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

# Import translation services
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from google.cloud import translate_v2 as translate
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False

log = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.workers.translation.translate_transcript")
def translate_transcript(self, meeting_id: str, target_language: str = "en") -> Dict[str, Any]:
    """
    Translate the transcript content to target language.
    Called after transcript is finalized.
    """
    try:
        asyncio.run(_translate_meeting_transcript(meeting_id, target_language))
        return {"status": "completed", "meeting_id": meeting_id, "target_language": target_language}
    except Exception as e:
        log.error(f"Failed to translate transcript for {meeting_id}: {e}", exc_info=True)
        raise self.retry(countdown=60, max_retries=3)


async def _translate_meeting_transcript(meeting_id: str, target_language: str):
    """Translate transcript content."""
    # Convert meeting_id to UUID if it's a string
    if isinstance(meeting_id, str):
        meeting_id = uuid.UUID(meeting_id)
    
    async with AsyncSessionLocal() as db:
        # Import here to avoid circular imports
        from app.db.models.transcript_chunk import TranscriptChunk
        
        # Get or create transcript
        result = await db.execute(
            select(Transcript).where(Transcript.meeting_id == meeting_id)
        )
        transcript = result.scalar_one_or_none()

        # If no transcript exists, create one from chunks
        if not transcript:
            # Get all transcript chunks for this meeting
            chunks_result = await db.execute(
                select(TranscriptChunk)
                .where(TranscriptChunk.meeting_id == meeting_id)
                .order_by(TranscriptChunk.start_time)
            )
            chunks = chunks_result.scalars().all()
            
            if not chunks:
                log.warning(f"No transcript chunks found for meeting {meeting_id}")
                return
            
            # Combine chunks into one transcript
            combined_text = "\n".join([chunk.text for chunk in chunks if chunk.text])
            primary_language = chunks[0].language if chunks else "en"
            
            # Create transcript record
            transcript = Transcript(
                id=uuid.uuid4(),
                meeting_id=meeting_id,
                content_raw=combined_text,
                primary_language=primary_language,
            )
            db.add(transcript)
            await db.commit()
            await db.refresh(transcript)

        # If transcript has no content, return
        if not transcript.content_raw:
            return

        # Check if already translated
        if transcript.content_translated and transcript.primary_language == target_language:
            return

        # Detect primary language if not set
        source_lang = transcript.primary_language or await _detect_language(transcript.content_raw)

        # Translate the content
        translated_text = await _translate_text(transcript.content_raw, source_lang, target_language)

        if translated_text:
            # Update transcript
            await db.execute(
                update(Transcript)
                .where(Transcript.id == transcript.id)
                .values(
                    content_translated=translated_text,
                    primary_language=source_lang,
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()

            # Trigger MOM generation now that we have the translated transcript
            from app.workers.mom import generate_mom_task
            generate_mom_task.delay(str(meeting_id))

        else:
            log.warning(f"Translation failed for meeting {meeting_id}")


async def _detect_language(text: str) -> str:
    """Detect primary language of text using OpenAI."""
    try:
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            return await _detect_language_with_openai(text)
        elif GOOGLE_TRANSLATE_AVAILABLE and settings.GOOGLE_AI_API_KEY:
            translate_client = translate.Client()
            result = translate_client.detect_language(text)
            return result["language"]
        else:
            # Simple heuristic detection
            if any(word in text.lower() for word in ["the", "and", "is", "in", "to", "of"]):
                return "en"
            elif any(word in text.lower() for word in ["el", "la", "de", "que", "y", "en"]):
                return "es"
            elif any(word in text.lower() for word in ["le", "la", "de", "et", "à", "un"]):
                return "fr"
            else:
                return "en"  # Default to English
    except Exception as e:
        log.error(f"Language detection failed: {e}")
        return "en"


async def _translate_text(text: str, source_lang: str, target_lang: str) -> Optional[str]:
    """Translate text using configured service."""
    if source_lang == target_lang:
        return text

    try:
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            return await _translate_with_openai(text, source_lang, target_lang)
        elif GOOGLE_TRANSLATE_AVAILABLE and settings.GOOGLE_AI_API_KEY:
            return await _translate_with_google(text, source_lang, target_lang)
        else:
            # Mock translation for development
            log.warning("No translation service configured, using mock translation")
            return f"[Mock translation to {target_lang}] {text}"
    except Exception as e:
        log.error(f"Translation failed: {e}")
        return None


async def _translate_with_openai(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text using OpenAI GPT."""
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Map language codes to full names
    lang_names = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ja": "Japanese",
        "zh": "Chinese",
        "ko": "Korean",
    }
    
    source_lang_name = lang_names.get(source_lang.lower(), source_lang)
    target_lang_name = lang_names.get(target_lang.lower(), target_lang)
    
    prompt = f"Translate the following text from {source_lang_name} to {target_lang_name}. Only return the translated text, nothing else.\n\nText: {text}"
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional translator."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )
    
    return response.choices[0].message.content.strip()


async def _detect_language_with_openai(text: str) -> str:
    """Detect language using OpenAI."""
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    prompt = f"What language is this text written in? Respond with only the language code (e.g., 'en', 'es', 'fr').\n\nText: {text[:200]}"
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a language detection system."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
    )
    
    detected = response.choices[0].message.content.strip().lower()
    # Extract just the language code if response is longer
    if len(detected) > 3:
        detected = detected.split()[0]
    return detected or "en"


async def _translate_with_google(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text using Google Translate API."""
    translate_client = translate.Client()

    result = translate_client.translate(text, target_language=target_lang, source_language=source_lang)
    return result["translatedText"]