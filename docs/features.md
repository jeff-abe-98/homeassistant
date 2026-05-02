# Feature Specifications

**Last updated:** 2026-05-02

Each section defines the behavior for one feature in detail — inputs, outputs, edge cases, and open questions.

---

## Feature: Weather

**Trigger phrases:** "What's the weather?", "Weather today", "Will it rain?", "What's the forecast?"

**Behavior:**
- Fetch full weather data for Chicago, IL
- Pass raw data to local LLM to generate a natural spoken response
- LLM decides what's most relevant (temperature, precipitation chance, wind, etc.)
- No rigid template — response should vary based on conditions

**Data source:** TBD (OpenWeatherMap, weather.gov, or similar)

**Edge cases:**
- "This weekend" → multi-day forecast
- "Right now" → current conditions only

---

## Feature: CTA L Train — Blue Line

**Trigger phrases:** "When's the next train?", "How long until the Blue Line?", "Next train toward O'Hare?"

**Behavior:**
- Default stop: Western & Milwaukee Ave (Blue Line)
- Real-time arrivals via CTA Train Tracker API
- Support directional queries: toward O'Hare (northwest) or toward Forest Park (southeast)
- Respond with next 1–2 arrival times and destination

**API:** CTA Train Tracker API (requires free API key from transitchicago.com)

**Edge cases:**
- Service alerts / delays → mention if present
- Late night (Blue Line runs 24/7, but less frequent)

---

## Feature: Google Calendar

**Trigger phrases:** "What do I have today?", "Add a dentist appointment Thursday at 3", "What's on my calendar this week?"

**Behavior:**
- Read: return events for the requesting user for today / specified date range
- Write: parse natural language date/time and create event
  - If Emily adds an event, title is prefixed with "Emily " (e.g., "Emily Dentist")
  - If owner adds an event, no prefix needed (or agreed prefix TBD)
- Shared Google Calendar between both users

**Auth:** Google Calendar API (OAuth2 — setup required)

**Edge cases:**
- Ambiguous time ("Thursday" when it's already Friday) → confirm with user
- Conflicting events → mention conflict when adding
- Unknown speaker adds event → ask "Who's this?" before adding

---

## Feature: Todo Lists (Google Tasks)

**Trigger phrases:** "Add oat milk to my list", "What's on my list?", "Mark eggs as done", "Read Emily's list" (owner only?)

**Behavior:**
- Two Google Task lists: "Owner" and "Emily"
- Add items: append to the requesting user's list
- Read items: read back all incomplete tasks
- Complete items: mark done by name or position ("the first one", "eggs")

**Auth:** Google Tasks API — shares OAuth2 credentials with Google Calendar (one setup for both)

**Edge cases:**
- "Add to both lists" → confirm before doing
- Item not found when checking off → ask for clarification

---

## Feature: Music Playback

**Trigger phrases:** "Play some jazz", "Play my Discover Weekly", "Pause", "Skip", "Turn it up"

**Behavior:**
- Identify speaker to determine service:
  - Emily → Spotify
  - Owner → Apple Music
- Audio output: Hisense TV speakers
- Controls: play, pause, skip, volume up/down, search by artist/song/playlist/mood

**Both users → Spotify (separate accounts):**
- Spotify Connect API — targets Fire TV as the active playback device
- Each user's Spotify account is linked to their voice profile
- Assistant sends playback commands to the correct account based on speaker ID

**Edge cases:**
- Unknown speaker requests music → ask who they are
- TV not available → fallback to Pi audio output

---

## Feature: TV Control (Hisense)

**Trigger phrases:** "Put on Seinfeld", "Open Netflix", "Turn on the TV", "Change to HDMI 1"

**Behavior:**
- Queue/play a TV show by name if Hisense API supports it
- Basic controls: power on/off, input switching, app launching (Netflix, etc.)
- Music-through-TV is a prerequisite and higher priority than show control

**Implementation path (to research):**
1. Android TV API — if TV runs Android TV
2. Hisense RemoteNOW / proprietary API
3. HDMI-CEC via Raspberry Pi
4. IR blaster (last resort)

**Open questions:**
- Exact Hisense model number?
- Does it run Android TV or Vidaa OS?

---

## Feature: Autonomous Tool Creation

**Trigger:** Any request the assistant cannot fulfill with existing tools

**Behavior:**
1. Assistant responds: "I don't know how to do that yet, but I'll figure it out."
2. In background: LLM attempts to design and implement a new tool/plugin
3. New tool is tested in a sandbox
4. If successful: tool is registered and user is notified ("I can do that now — want to try?")
5. If it fails: user is notified, optionally with what was attempted

**Constraints:**
- New tools run in a sandboxed environment before being trusted
- No tool should be able to access the network or filesystem arbitrarily without approval
- Generated tools follow the same plugin interface as built-in tools

**Open questions:**
- What LLM is capable enough to write reliable tool code on modest hardware?
- How is tool sandboxing implemented? (Docker, subprocess isolation, etc.)
- Does the user get to review/approve generated tools before they run?
