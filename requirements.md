# Home Assistant — Project Requirements

**Project:** Personal Home Assistant  
**Household:** Two primary users (owner + Emily)  
**Location:** Chicago, IL  
**Last updated:** 2026-05-02  
**Phase:** Requirements complete — ready for technical planning

---

## Overview

A voice-activated, locally-hosted AI home assistant for a Chicago apartment. It listens for a wake word, identifies who is speaking, and provides personalized responses and actions. When asked to do something it doesn't yet know how to do, it can autonomously build the capability in the background.

---

## Users

| User | Voice Profile | Music | Todo List | Calendar |
|------|--------------|-------|-----------|----------|
| Owner | Recognized | Spotify | Owner (Google Tasks) | Personal events (Google Calendar) |
| Emily | Recognized | Spotify | Emily (Google Tasks) | "Emily [Event]" prefix (Google Calendar) |
| Guest/Unknown | Not recognized | N/A | N/A | Ask who they are if context requires it |

**Voice recognition behavior:**
- If speaker is identified: proceed with personalized behavior silently
- If speaker is unknown and the request is personal (calendar, todos, music): ask "Who's this?"
- If speaker is unknown and the request is generic (weather, train): answer without asking

---

## Hardware

| Component | Role |
|-----------|------|
| Raspberry Pi (living room) | Always-on voice interface — microphone input, speaker/TV audio output |
| Home server (TBD, not yet set up) | Runs local AI models and heavier workloads |
| Hisense TV (living room) | Primary audio/visual output — music plays through TV speakers |

---

## Core Features

### 1. Wake Word Activation
- Always listening for a custom wake word (TBD — to be decided later)
- After wake word, records voice input and processes request
- Should be responsive and low-latency

### 2. Voice Recognition / Speaker Identification
- Maintains voice profiles for known users (Owner, Emily)
- Identifies speaker before processing personal requests
- Unknown speakers handled gracefully (see Users section)

### 3. Weather
- Full weather data for Chicago (current conditions + forecast)
- Uses an AI layer to parse the raw data source and generate a natural spoken response
- No rigid template — AI should interpret and summarize what's most relevant

### 4. CTA L Train Schedules
- Specifically: Blue Line, Western & Milwaukee Ave stop
- Real-time arrivals ("When's the next Blue Line train?")
- Should handle directional queries (toward O'Hare vs Forest Park)

### 5. Google Calendar
- Read events for the requesting user
- Add events — if Emily adds one, it is added with her name if shared (e.g., "Emily Doctors Appointment")
- Shared calendar between both users
- Natural language input ("I have a dentist appointment Thursday at 3pm")

### 6. Todo Lists (Google Tasks)
- Backed by Google Tasks — one task list per user ("Owner" and "Emily")
- Shares the same Google OAuth as Calendar (one auth setup for both)
- Capabilities: add items, read items back, complete/check off items
- Requests are routed to the correct user's list based on voice identification
- Example: "Add oat milk to the list" → added to the speaking user's list

### 7. Music Playback
- Both users → Spotify (separate accounts)
- Audio output via Amazon Fire TV speakers
- Basic controls: play, pause, skip, volume, search by song/artist/playlist/mood
- Spotify Connect used to target Fire TV as the playback device

### 8. TV Control (Amazon Fire TV OS 11)
- Primary method: ADB over local network
- Queue and play TV shows by name, launch streaming apps (Netflix, etc.)
- Music playback through TV is a hard requirement; show control is best-effort

### 9. Autonomous Tool Creation
- If the assistant is asked to do something it cannot currently do, it should:
  1. Acknowledge it doesn't know how to do that yet
  2. Attempt to build the capability in the background (using AI to generate and install the tool/plugin)
  3. Notify the user when the new capability is ready
- This is a differentiating feature — treat it as a first-class capability

---

## Non-Functional Requirements

| Requirement | Detail |
|-------------|--------|
| Privacy | All AI runs locally — no cloud AI for personal data |
| Performance | Must work on modest hardware (lightweight local models) |
| Latency | Wake word to response should feel natural, not sluggish |
| Reliability | Should run continuously without manual restarts |
| Extensibility | Architecture must support adding new features/tools over time |

---

## Future Phases

Features that are intentionally deferred — not in scope for early phases but planned:

| Phase | Feature | Notes |
|-------|---------|-------|
| 3–4 | Custom music recommendation system | Per-user models that learn taste over time; Owner and Emily have separate recommendation profiles trained on their listening history |

---

## Out of Scope (for now)

- Smart home device control (lights, thermostat, locks)
- Multi-room audio / multiple microphones
- Mobile app interface
- Guests having persistent profiles
- Non-English language support
