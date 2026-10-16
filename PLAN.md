# Raven Plays the Spire — Project Plan

**Goal:** Enter Mistral's "Le Chonk wants to play" Discord challenge with Raven, a goth gamer girl AI (adult, 18+) who plays *Slay the Spire* using **Mistral Large 4** (`mistral-large-4`). After the challenge, Raven grows into a streamer persona.

**Deadline:** Oct 29, 2026, 5:59 PM. Check the timezone in the Discord post.
**Team:** Darrell, with Claude (planning and design) and Claude Code (implementation).
**Machine:** Windows laptop (GTX 1070) for the challenge. Later moves to the desktop.

## How the challenge is judged

| Criterion | How we address it |
|---|---|
| Fun | Raven's personality and in-character commentary, an overlay, and a voice if time allows |
| Complexity | A full roguelike run: combat, deckbuilding, map pathing, events, shops. Text state plus vision. |
| Performance | Benchmarked fixed-seed runs: floors reached and wins, compared with a random player and with Darrell's first run (died to the Act 1 boss) |
| Reproducibility | A README a stranger can follow, tested from scratch before submitting |

**Submission needs:** a video, a public GitHub repo with a full README, and a "how it was built" note covering people, tools and OSS used.

## Decisions made

1. **Decisions focus on winning.** Raven is a competitive gamer, and every move also carries a short in-character line from her.
2. **Vision:** decisions use the structured text state, which is accurate and cheap. Screenshots of the game feed her commentary and big moments such as bosses, elites, rare cards and death.
3. **Voice:** included if time allows, otherwise on-screen text only.
4. **Workflow:** plan in Claude chat, build with Claude Code in `D:\dev\raven`.

## Architecture

```
Slay the Spire ─ CommunicationMod ─stdin/stdout─► raven (Python) ─HTTPS─► Mistral API (mistral-large-4)
                                                      │
                                                      ├─ logs/ (every decision, replayable)
                                                      └─ overlay (what Raven sees, thinks and says)
```

- **CommunicationMod** (Steam Workshop) launches our script and exchanges JSON state and text commands with it.
- Each decision is one API call. The model must answer with one tool call (`play_card`, `end_turn`, `choose`, …) that includes `reasoning` and a `raven_says` line.
- The harness validates every move against the real game state. Illegal moves go back to the model as errors, with a safe fallback after 3 tries.
- **Card and relic text** isn't included in the game state. We read it from the player's own game install (the localization files in `desktop-1.0.jar`), so it's accurate and nothing copyrighted gets redistributed.

## Repo layout

```
raven/
  raven/
    games/spire/   # CommunicationMod protocol, state rendering, action validation
    brain/         # Mistral client, tools, prompts, retries, cost tracking
    persona/       # Raven's character sheet and voice
    overlay/       # stream/video overlay (browser source for OBS)
  scripts/         # benchmark runs, replay viewer, etc.
  logs/            # gitignored
  .env.example     # MISTRAL_API_KEY=...  (real .env is gitignored)
  README.md  PLAN.md  CLAUDE.md  requirements.txt
```

## Milestones

### M1: Plumbing (Oct 17–19)
- [ ] Initialize the git repo and create the public GitHub repo
- [ ] Python project skeleton: venv, requirements, `.env` handling
- [ ] CommunicationMod config pointing at our launcher. The game launches the script.
- [ ] **Random player** completes a run (no API cost). This proves the plumbing.
- [ ] Mistral client with a smoke test calling `mistral-large-4`
- [ ] Raven completes a full run on `mistral-large-4`. Bad play is fine.
- [ ] Decision log (JSONL) and run results

### M2: Make her good (Oct 20–23)
- [ ] Card and relic descriptions from the game files in the prompt
- [ ] Strategy prompt tuning, notes-to-self memory, map lookahead
- [ ] Benchmark script: N fixed-seed runs, reporting floor and win rate, with random as the baseline
- [ ] Track cost per run

### M3: Make her Raven (Oct 22–25)
- [ ] Persona sheet: voice, attitude, catchphrases, likes and dislikes
- [ ] `raven_says` on every move, plus bigger reactions to big moments
- [ ] Vision: screenshots of the game window for commentary moments
- [ ] Overlay showing her line, what she's planning, HP and floor
- [ ] Optional: voice (TTS)

### M4: Ship it (Oct 26–28, buffer Oct 29)
- [ ] Record the video: setup, a highlight run, her reactions, results
- [ ] README: full setup from zero, troubleshooting
- [ ] Reproducibility test: a fresh clone following only the README
- [ ] "How it was built" section
- [ ] Post to #challenges-submissions

## After the challenge
Move to the desktop. Add a live voice, an avatar, chat interaction and more games. Raven becomes a streamer.
