"""
email_service.py — Email dispatch service for sending MOM emails.

Uses the Resend SDK when RESEND_API_KEY is configured.
Falls back to a mock/log mode for local development.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import settings

log = logging.getLogger(__name__)


# ── HTML template ──────────────────────────────────────────────────────────────

def _build_html(
    meeting_title: str,
    meeting_date: str,
    participants: List[Dict[str, Any]],
    summary: Optional[str],
    key_decisions: Optional[str],
    action_items: List[Dict[str, Any]],
) -> str:
    """Build a polished HTML email for the MOM."""

    # Participants list
    participant_names = ", ".join(
        p.get("name") or p.get("email") or "Unknown"
        for p in participants
    ) or "—"

    # Key decisions → HTML list items
    if key_decisions:
        decisions_html = "".join(
            f"<li style='margin-bottom:6px'>{line.lstrip('- •').strip()}</li>"
            for line in key_decisions.splitlines()
            if line.strip().lstrip("- •")
        )
        decisions_section = f"<ul style='padding-left:20px;color:#334155'>{decisions_html}</ul>"
    else:
        decisions_section = "<p style='color:#94a3b8'>No key decisions recorded.</p>"

    # Action items → HTML table rows
    if action_items:
        rows_html = ""
        priority_colors = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}
        for item in action_items:
            prio = str(item.get("priority", "medium")).lower()
            color = priority_colors.get(prio, "#f59e0b")
            deadline = item.get("deadline") or "—"
            assignee = item.get("assignee_name") or item.get("assignee_email") or "—"
            task = item.get("task", "")
            rows_html += f"""
            <tr>
              <td style='padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#1e293b'>{task}</td>
              <td style='padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#475569'>{assignee}</td>
              <td style='padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#475569'>{deadline}</td>
              <td style='padding:10px 12px;border-bottom:1px solid #e2e8f0'>
                <span style='background:{color}20;color:{color};padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600'>{prio.upper()}</span>
              </td>
            </tr>"""
        action_table = f"""
        <table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-top:8px'>
          <thead>
            <tr style='background:#f8fafc'>
              <th style='padding:10px 12px;text-align:left;font-size:13px;color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0'>Task</th>
              <th style='padding:10px 12px;text-align:left;font-size:13px;color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0'>Assignee</th>
              <th style='padding:10px 12px;text-align:left;font-size:13px;color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0'>Deadline</th>
              <th style='padding:10px 12px;text-align:left;font-size:13px;color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0'>Priority</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>"""
    else:
        action_table = "<p style='color:#94a3b8'>No action items extracted.</p>"

    summary_html = summary or "No summary available."

    return f"""<!DOCTYPE html>
<html lang='en'>
<head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'></head>
<body style='margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif'>
  <table width='100%' cellpadding='0' cellspacing='0'>
    <tr><td align='center' style='padding:40px 16px'>
      <table width='600' cellpadding='0' cellspacing='0' style='max-width:600px;width:100%'>

        <!-- Header -->
        <tr><td style='background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);border-radius:12px 12px 0 0;padding:32px 40px'>
          <p style='margin:0 0 4px;color:#94a3b8;font-size:13px;letter-spacing:0.05em;text-transform:uppercase'>AI Meeting Assistant</p>
          <h1 style='margin:0;color:#f8fafc;font-size:24px;font-weight:700;line-height:1.3'>📋 Minutes of Meeting</h1>
          <p style='margin:8px 0 0;color:#7dd3fc;font-size:15px'>{meeting_title}</p>
        </td></tr>

        <!-- Meta -->
        <tr><td style='background:#1e293b;padding:16px 40px'>
          <table width='100%'><tr>
            <td style='color:#94a3b8;font-size:13px'>📅 <span style='color:#e2e8f0'>{meeting_date}</span></td>
            <td style='color:#94a3b8;font-size:13px'>👥 <span style='color:#e2e8f0'>{participant_names}</span></td>
          </tr></table>
        </td></tr>

        <!-- Body -->
        <tr><td style='background:#ffffff;padding:32px 40px;border-radius:0 0 12px 12px'>

          <!-- Summary -->
          <h2 style='margin:0 0 12px;font-size:16px;font-weight:700;color:#0f172a;border-left:3px solid #3b82f6;padding-left:10px'>Executive Summary</h2>
          <p style='margin:0 0 28px;color:#475569;line-height:1.7;font-size:15px'>{summary_html}</p>

          <!-- Key Decisions -->
          <h2 style='margin:0 0 12px;font-size:16px;font-weight:700;color:#0f172a;border-left:3px solid #8b5cf6;padding-left:10px'>Key Decisions</h2>
          <div style='margin-bottom:28px'>{decisions_section}</div>

          <!-- Action Items -->
          <h2 style='margin:0 0 12px;font-size:16px;font-weight:700;color:#0f172a;border-left:3px solid #f59e0b;padding-left:10px'>Action Items</h2>
          {action_table}

        </td></tr>

        <!-- Footer -->
        <tr><td style='padding:24px 40px;text-align:center'>
          <p style='margin:0;color:#94a3b8;font-size:12px'>
            Sent by <strong>AI Meeting Assistant</strong> · Auto-generated MOM<br>
            <span style='color:#cbd5e1'>Do not reply to this email.</span>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Service function ───────────────────────────────────────────────────────────

async def send_mom_email(
    mom_id: str,
    meeting_title: str,
    meeting_date: datetime,
    participants: List[Dict[str, Any]],
    summary: Optional[str],
    key_decisions: Optional[str],
    action_items: List[Dict[str, Any]],
    to_emails: List[str],
) -> Dict[str, Any]:
    """
    Send MOM email to the given addresses.

    Returns a dict with ``{"status": "sent"}`` or ``{"status": "mock"}`` when
    the API key is not configured.
    """
    html_body = _build_html(
        meeting_title=meeting_title,
        meeting_date=meeting_date.strftime("%B %d, %Y"),
        participants=participants,
        summary=summary,
        key_decisions=key_decisions,
        action_items=action_items,
    )

    subject = f"MOM: {meeting_title} — {meeting_date.strftime('%d %b %Y')}"

    if not settings.RESEND_API_KEY:
        log.warning(
            "RESEND_API_KEY not set — skipping real email send for MOM %s. "
            "Would have sent to: %s",
            mom_id,
            to_emails,
        )
        return {"status": "mock", "recipients": to_emails}

    try:
        import resend  # type: ignore[import]

        resend.api_key = settings.RESEND_API_KEY

        response = resend.Emails.send({
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
            "to": to_emails,
            "subject": subject,
            "html": html_body,
        })

        log.info("MOM email sent for %s. Resend id: %s", mom_id, response.get("id"))
        return {"status": "sent", "resend_id": response.get("id"), "recipients": to_emails}

    except ImportError:
        log.warning("resend package not installed — skipping email for MOM %s", mom_id)
        return {"status": "mock", "recipients": to_emails}

    except Exception as exc:
        log.error("Failed to send MOM email for %s: %s", mom_id, exc, exc_info=True)
        raise
