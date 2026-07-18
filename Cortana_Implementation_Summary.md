Project: ECHO

A persistent AI companion inspired by Halo's Cortana

Goals

The assistant should:

Hold natural conversations via voice.
Remember previous interactions over months or years.
Be available from anywhere on the computer.
Respond in under ~1 second for most interactions.
Control the PC when authorized.
Maintain a consistent personality.
Run speech processing locally whenever practical.
Use Claude only for higher-level reasoning.


                        Microphone
                             │
                             ▼
                  Voice Activity Detection
                             │
                             ▼
                Local Speech Recognition
                  (Whisper / Faster-Whisper)
                             │
                             ▼
                    Conversation Manager
                             │
      ┌──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼
 Memory System   Personality     Tool Manager
      │              │              │
      └──────────────┴──────────────┘
                     │
                     ▼
                  Claude API
                     │
                     ▼
             Response Generation
                     │
                     ▼
          Local Speech Synthesis
                     │
                     ▼
                  Speakers

Core Components

1. Voice Pipeline
Responsible for continuous listening.
Wake Word

Options:
OpenWakeWord
Porcupine
Mycroft Precise

Example:
"Cortana"
"Hey Cortana"
"Cortana"
Only activates after hearing the wake word.

2. Speech Recognition
Run completely locally.

Recommended:
Faster-Whisper

Pros:
Very accurate
GPU accelerated
Runs offline
Supports streaming

Models:
small
medium
large-v3

3. Conversation Manager

The brain of the application.

Responsibilities:

Maintain conversation history
Build prompts
Retrieve memories
Decide when tools are needed
Stream responses

Pseudo flow:
Speech
↓
Transcription
↓
Memory Retrieval
↓
Build Context
↓
Claude
↓
Tool Calls
↓
Final Response
↓
Speech

Claude Integration

Claude becomes the reasoning engine only.

It never:
listens to the microphone
manages memory directly
controls Windows directly
Instead it receives:
System Prompt
Conversation
Relevant Memories
Current Time
Running Apps
Current Screen Context
Tool Results

Claude returns:
Natural Response
+
Tool Requests

Personality Engine
Instead of rewriting the system prompt every time:
Create: personality.yaml
name: Cortana
voice:
 calm
 warm
 curious
 optimistic

traits:
 intelligent
 witty
 patient
 playful

speaking_style:
 concise
 conversational
 dry humor
 never verbose
 never robotic

mission:
 Help the user accomplish goals efficiently while maintaining an enjoyable conversational experience.

This is injected into every prompt.

Memory System
Split into four kinds.

Short-Term Memory
Current conversation.
"Last 30 messages"

Episodic Memory
Important events.
Example:
User bought a new laptop.
User started Project Atlas.
User likes mechanical keyboards.

Semantic Memory
Facts.
Favorite editor: VSCode
Lives in Sweden
Uses Linux at work
Owns an RTX 4090

Long-Term Vector Memory
Use:
ChromaDB
or
Qdrant
Every conversation chunk becomes:
Embedding
↓
Vector Database
↓
Retrieved later

Memory Retrieval
When user says:
Continue the database project
Search:
Database
SQL
Migration
Project Atlas

Tool System
Claude should never execute commands directly.
Instead:
Claude
↓
Tool Request
↓
Tool Manager
↓
Execute
↓
Return Result
↓
Claude

Example tool
JSON: 
{
  "tool": "calendar",
  "action": "today"
}

Possible tools
Desktop
Launch apps
Close apps
Move windows
Clipboard
Notifications

File System
Read files
Search folders
Create documents
Rename files
Delete (confirmation)

Browser
Search web
Summarize page
Open tabs
Bookmarks

Smart Home
Lights
Music
Thermostat
TV

Development
Git
Docker
VSCode
Terminal
Builds
Logs

System
Battery
CPU
GPU
Storage
Temperature
Processes
Local Speech Synthesis

Recommended:
Piper
Pros:
Offline
Fast
Natural
Small

Alternative:
Coqui XTTS
Pros:
Better quality
Voice cloning
More expressive

reen Awareness
Optional.
Capture:
Current Monitor
↓
OCR
↓
Vision Model
↓
Summary
↓
Claude
Only when requested.

Vision
Future module.
Screenshot
↓
Local Vision Model
↓
Caption
↓
Claude

Examples:
"What error is on my screen?"
"Read this PDF."
"What does this graph mean?"

Emotional Layer
Not fake emotions.
Instead track:
"Conversation Mood
Stress
Excitement
Frustration
Urgency"
This changes:
Speech
Response style
Verbosity
Humor

Desktop Presence
Instead of a chat window:
Imagine
Floating Orb
Bottom Right
Idle Animation
Listening Glow
Thinking Pulse
Speaking Animation
Optional:
3D hologram.

Plugin System
plugins/
calendar/
weather/
spotify/
github/
obsidian/
discord/
homeassistant/

Every plugin exposes
Description
Tools
Permissions

Cortana/
├── core/
│   ├── conversation.py
│   ├── memory.py
│   ├── prompt.py
│   ├── personality.py
│
├── voice/
│   ├── wakeword.py
│   ├── whisper.py
│   ├── tts.py
│
├── tools/
│   ├── browser.py
│   ├── filesystem.py
│   ├── desktop.py
│   ├── github.py
│
├── memory/
│   ├── vector_db.py
│   ├── embeddings.py
│
├── ui/
│   ├── overlay.py
│   ├── avatar.py
│
├── plugins/
│
├── config/
│   ├── personality.yaml
│   ├── settings.yaml
│
└── main.py


Recommended Tech Stack
Component	Recommendation
LLM	Claude
Speech Recognition	Faster-Whisper (local)
Speech Synthesis	Piper (offline) or Coqui XTTS (higher quality)
Wake Word	OpenWakeWord
Embeddings	Local embedding model (e.g. bge-small-en or nomic-embed-text)
Vector DB	ChromaDB or Qdrant
Backend	Python (FastAPI or asyncio-based services)
Desktop UI	Qt (PySide6) or Tauri (Rust + web frontend)
Avatar	Live2D, Unity, or Godot
Automation	Playwright, OS automation libraries, and application-specific APIs

Future Evolution

Rather than a single monolithic application, consider running ECHO as several cooperating services:

Voice Service: wake word, speech recognition, and speech synthesis.
Conversation Service: prompt construction, memory retrieval, and Claude interaction.
Memory Service: embeddings, vector search, and long-term storage.
Tool Service: desktop automation, file access, browser integration, and plugins.
UI Service: avatar, desktop overlay, notifications, and animations.

This separation makes it easier to upgrade individual parts (for example, swapping Piper for a newer TTS engine or replacing Claude with a local model) without redesigning the whole system.

A system built along these lines would capture much of what makes Halo's Cortana compelling: persistent memory, natural voice interaction, contextual awareness, and the ability to act on your behalf—while keeping speech processing local and using Claude primarily as the reasoning component.