# CLAUDE.md — project rules for Claude Code

Read `PLAN.md` first. It holds the agreed plan and milestones. Work milestone by milestone, and stop to check in with Darrell at the end of each task rather than running ahead.

## Hard rules
- **Model:** always `mistral-large-4`. Never `mistral-large-latest`, which is a different model.
- **API key:** loaded from `.env` (`MISTRAL_API_KEY`), which is gitignored. Never print, log or commit the key. Commit `.env.example` with a placeholder only.
- **stdout belongs to the game.** CommunicationMod reads our stdout as commands, so never `print()` in code that runs under the game. Log to files in `logs/`.
- Windows 11, PowerShell, Python 3.13. Use a venv (`.venv`) and `requirements.txt`.
- Keep game-specific code in `raven/games/spire/`, model code in `raven/brain/`, and personality in `raven/persona/`. Raven will play other games later.

## CommunicationMod protocol (verified against its README)
- The game launches our process and waits for us to print `ready`. There's a timeout of about 10 seconds.
- The game sends one JSON line per stable state: `available_commands`, `ready_for_command`, `in_game`, `game_state`. On failure it sends `{"error": ..., "ready_for_command": true}`.
- Commands, case-insensitive, one per line:
  - `START <class> [ascension] [seed]`
  - `PLAY <card_index> [target_index]`: **card index is 1-based**, target index is 0-based
  - `END`
  - `POTION Use|Discard <slot> [target_index]`
  - `CHOOSE <index|name>`: 0-based into `game_state.choice_list`
  - `PROCEED` (also confirm), `RETURN` (also skip, cancel, leave)
  - `STATE`, `WAIT <frames>`, `KEY`, `CLICK`
- Card objects have no description text. Card and relic text comes from the game's own localization files.
- Known quirk: taking or buying a potion with full slots silently does nothing.
- Config: `%LOCALAPPDATA%\ModTheSpire\CommunicationMod\config.properties`, with `command=...` (escape `:` and `\`). Debug output is in `communication_mod_errors.log` in the game folder.
- Mods installed via Steam Workshop: ModTheSpire, BaseMod, CommunicationMod.

## Git workflow
- **`main`** is the production build: always working, always passing. Never commit directly to it.
- **`development`** is the integration branch. Never commit directly to it either.
- For every feature or fix, branch off `development` as `feature/<short-name>` or `fix/<short-name>`. Write the code **and its tests** on that branch.
- **Merging into `development`:** open a PR. The full test suite must pass. Then merge.
- **Promoting to `main`:** open a PR from `development` to `main`. The full test suite must pass again.
- GitHub Actions runs `pytest` on every PR, and branch protection on `main` and `development` requires it to pass.
- Small, focused commits with clear messages. Ask Darrell before merging anything into `main`.

## Testing
- `pytest`, with tests in `tests/` mirroring the package layout.
- Tests must run **without the game and without an API key**, since CI has neither. Use recorded or sample game-state JSON fixtures, a fake game process for protocol tests, and a mocked Mistral client.
- Anything that calls the real Mistral API (like `scripts/smoke_test.py`) is a manual script, not part of the test suite.
