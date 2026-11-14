# Teardown: Meta Global AI Developer Hackathon winners' demo videos (Nov 2026)

**Sources:**
- The organisers' winners email.
- Each video's YouTube metadata and captions.
- Each winner's public GitHub repo.

**Not done:** I did not download or watch the video frames. Anything about visuals comes from descriptions, captions and repo files. **Evidence** marks what a repo or the metadata states. **Inference** marks my reading of it.

| Project (place) | Length | Format |
|---|---|---|
| Punchwalk (Startup 1st) | 2:53 | First-person narrator, "I grew up in a construction family". Real Ray-Ban Meta glasses footage plus app screens. Each Meta model is named as it acts |
| Formwright (Startup 2nd) | 2:58 | **No voice, music only**, so on-screen text carries it. "The film follows one real run: 64 tool calls, with refusals" |
| ORCA (Startup 3rd) | 3:00 | Narrator, burned-in captions, brand motion cards. Story structured on the name: O·R·C·A, one beat each |
| ControlAnything (Indie 1st) | 2:12 | First-person narrator, filmed through a real Quest 3. YouTube chapters (Intro / How it works / Demos) |
| Gatekeeper (Indie 2nd) | 2:50 | Solo first-person narrator. A staged but harmless live attack (a fake malware package blocked on camera) |
| Basement Ready (Indie 3rd) | 2:08 | Narrator over a real phone video of a real basement. "No lidar, no special gear", and the answer is shown first |

## What they have in common (the pattern to copy)
1. **The hook is a real person's problem in one sentence**, often first person: "I grew up in a construction family", "This is a real basement in Ontario."
2. **Real footage, never mock-ups.** Real glasses, a headset, a phone video, live runs. Several state it outright: "filmed on a real Quest 3", "a real basement", "one real run".
3. **Each model or dataset is named once, with what it does**, e.g. "SAM 3.1 follows my hand to the spot".
4. **A proof moment:** a refusal, a check that fails then passes, or a confirmed real-world count ("48 packages it flagged are now confirmed malware").
5. **About 400 words in about 2:50.** Ours is 30 s, so scale that to about 70 words.
6. **Plain words.** ORCA's script keeps a "say this, not that" table (BIM → "3D designs", clearance → "room to spare"). Our deck draft has the same table.

## Tools (what's known vs inferred)
- **ORCA:**
  - **Evidence** (`docs/demo-video.md` in their repo):
    - Every shot was recorded as its own take in **Recordly**, an open-source desktop screen recorder that draws the cursor and zooms on each click.
    - A **Playwright** script (`web/scripts/record-demo.cjs`) drove the app in Chrome and told Recordly when to start and stop.
    - Title and step cards were generated as PNGs by a Node script (`video-cards.cjs`) in IBM Plex Sans, then placed on a **1920×1080 timeline**.
    - Brand motion (animated SVG/APNG logo reveals) is in `assets/brand/orca/motion`.
    - "Captions burned in (judges often watch muted); light music, none under the key lines."
    - They kept a written shot list with timings and planned cuts, and froze the script days before the deadline.
  - **Not stated:** which editor they used for the final cut.
- **Gatekeeper:** **Evidence:** `demo/prepare-recording.ps1` sets up a staged scenario (a local npm registry, a fake attacker listener, fake credentials) so every take is safe and reproducible. Takes were run in PowerShell. The editor is not stated.
- **Formwright:** **Evidence:** the film replays a real stored agent run (its app can replay any run's event log, `scripts/curate_demo.py`), so the footage is a real run without waiting on the model live.
- **Punchwalk / Basement Ready:** **Evidence:** a real device or phone capture, and the app is screen-recorded. Basement Ready's iOS app has its own `DemoCapture.swift` and `VideoWriter.swift` for recording.
- **Decks:** none of the six repos contains a pitch deck (no .pptx, Keynote, Slidev or Marp files). These were video-only submissions, so there is nothing to reverse-engineer for decks.
- **Inference, from the style only (unverified):**
  - The cursor-zoom look matches Recordly, Screen Studio, Cap or Focusee.
  - The music-under-voice edits with captions are typical of CapCut, Descript or DaVinci Resolve.

## What this means for us
- Script first, with a timed table and a plain-words list. Record each shot as its own scripted take, so retakes match.
- Use real data and real screens only. Our honest "two illusions" story is the proof moment.
- Burn in captions, add light music, and drop the music under the key line.
