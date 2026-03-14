"""
mom_service.py — LLM-powered MOM (Minutes of Meeting) generation service.
Uses Gemini 1.5 Pro with Instructor for structured output.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import instructor
import google.generativeai as genai
from pydantic import BaseModel, Field
from app.core.config import settings

log = logging.getLogger(__name__)

# Configure Gemini
if settings.GOOGLE_AI_API_KEY:
    genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
    client = instructor.from_gemini(
        client=genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config={"temperature": 0.1, "top_p": 0.8, "max_output_tokens": 8192}
        ),
        mode=instructor.Mode.GEMINI_JSON,
    )
else:
    client = None
    log.warning("GOOGLE_AI_API_KEY not set, MOM generation will be disabled")


# ── Pydantic Models for Structured Output ──────────────────────────────────────

class ActionItem(BaseModel):
    """Single action item extracted from meeting transcript."""
    task: str = Field(..., description="Clear, actionable task description")
    assignee_name: Optional[str] = Field(None, description="Name of person assigned to this task")
    assignee_email: Optional[str] = Field(None, description="Email of person assigned to this task")
    deadline: Optional[str] = Field(None, description="Deadline in YYYY-MM-DD format or relative like 'next week'")
    priority: str = Field("medium", description="Priority level: low, medium, high")


class MOMOutput(BaseModel):
    """Structured output from LLM for MOM generation."""
    summary: str = Field(..., description="2-3 sentence executive summary of the meeting")
    key_decisions: str = Field(..., description="Bullet points of key decisions made")
    action_items: List[ActionItem] = Field(..., description="List of action items extracted from the discussion")
    full_content: str = Field(..., description="Complete formatted MOM in markdown with sections")


# ── Service Functions ──────────────────────────────────────────────────────────

async def generate_mom(
    meeting_title: str,
    transcript_text: str,
    participants: List[Dict[str, Any]],
    meeting_date: datetime
) -> Dict[str, Any]:
    """
    Generate MOM from meeting transcript using Gemini + Instructor.

    Args:
        meeting_title: Title of the meeting
        transcript_text: Full transcript text (preferably translated to English)
        participants: List of participant dicts with 'name' and 'email' keys
        meeting_date: When the meeting occurred

    Returns:
        Dict with 'summary', 'key_decisions', 'action_items', 'full_content'
    """
    if not client:
        log.error("Gemini client not configured")
        return _generate_mock_mom(meeting_title, transcript_text, participants, meeting_date)

    try:
        # Format participants for context
        participant_names = [p.get("name", "Unknown") for p in participants if p.get("name")]
        participant_list = ", ".join(participant_names) if participant_names else "Unknown participants"

        # Create prompt
        prompt = f"""
You are an expert meeting assistant. Generate a comprehensive Minutes of Meeting (MOM) from the following transcript.

MEETING DETAILS:
- Title: {meeting_title}
- Date: {meeting_date.strftime('%Y-%m-%d')}
- Participants: {participant_list}

TRANSCRIPT:
{transcript_text}

INSTRUCTIONS:
1. Create a 2-3 sentence executive summary
2. List key decisions made (bullet points)
3. Extract all action items with assignees, deadlines, and priorities
4. Generate a complete formatted MOM in markdown

Be specific and actionable. If no action items are mentioned, return an empty list.
For deadlines, use YYYY-MM-DD format when possible, or relative terms like "next week".
Priorities should be: low, medium, high.
"""

        # Generate structured output
        result = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=MOMOutput,
            max_retries=3,
        )

        log.info(f"Successfully generated MOM for meeting: {meeting_title}")
        return result.model_dump()

    except Exception as e:
        log.error(f"Failed to generate MOM with Gemini: {e}", exc_info=True)
        return _generate_mock_mom(meeting_title, transcript_text, participants, meeting_date)


def _generate_mock_mom(
    meeting_title: str,
    transcript_text: str,
    participants: List[Dict[str, Any]],
    meeting_date: datetime
) -> Dict[str, Any]:
    """Fallback mock MOM generation when LLM is unavailable."""
    log.warning("Using mock MOM generation")

    return {
        "summary": f"This meeting covered {len(transcript_text.split())} words of discussion.",
        "key_decisions": "- Meeting occurred and was recorded\n- Transcript generated successfully",
        "action_items": [
            {
                "task": "Review meeting transcript",
                "assignee_name": participants[0].get("name") if participants else None,
                "assignee_email": participants[0].get("email") if participants else None,
                "deadline": "next week",
                "priority": "medium"
            }
        ],
        "full_content": f"""# Minutes of Meeting: {meeting_title}

**Date:** {meeting_date.strftime('%Y-%m-%d')}
**Participants:** {', '.join([p.get('name', 'Unknown') for p in participants])}

## Summary
This meeting covered {len(transcript_text.split())} words of discussion.

## Key Decisions
- Meeting occurred and was recorded
- Transcript generated successfully

## Action Items
- Review meeting transcript (Assignee: {participants[0].get('name') if participants else 'TBD'})

## Full Transcript
{transcript_text}
"""
    }