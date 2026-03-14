# AI Meeting Assistant: System Architecture

## Project Overview
This is a secure, real-time AI meeting assistant. It joins meetings via a bot, streams live audio/transcripts, translates Hindi and Marathi to English, generates Minutes of Meeting (MOMs), and automatically schedules extracted tasks.

## Tech Stack
- Backend Core: Node.js with Express
- Real-Time Streaming: Socket.IO
- Bot Provider: Recall.ai (or custom deployment)
- AI Processing: LLM for translation and task extraction
- Database: PostgreSQL or MongoDB

## Core System Components
- Authentication Module: Handles secure user login, session management, and route protection. No business logic executes without valid auth.
- Bot Manager: Controls the deployment endpoint, commanding the bot to join, record, and leave calls.
- Streaming Server: A Socket.IO implementation that receives live audio/text chunks from the active meeting.
- AI Processing Pipeline: Routes non-English audio to a translation layer, then passes the full English transcript to an LLM.
- Task Scheduler: Parses strict JSON output from the LLM to assign tasks and deadlines to specific users.