# Copilot instructions for PersonaOCEAN

Goal: Help AI coding agents be productive quickly in this repo by capturing real, current practices and patterns.

## What this repo is
- A minimal Discord bot that maps Big Five (OCEAN) scores to named archetypes and departments.
- Single-file bot logic in `main.py`, role taxonomy in `roles.yaml`, and a schema validator in `validate_roles.py`.
- No database. All state is in-memory and isolated per guild; data resets on restart.

## Architecture essentials (where things live)
- `main.py`
  - Discord client + slash commands using discord.py 2.x
  - Scoring: normalize each 0–120 input to −1..+1 via `(x-60)/60`, dot-product against each role’s pattern.
  - In-memory registry `companies: dict[guild_id -> {user_id -> {traits, role, dept}}]`.
  - Commands: `/ocean`, `/profile`, `/company`, `/departments`, `/summary`, `/help`, `/about`, `/forget`.
  - Utilities to follow in new code: `send_safe(...)`, `maybe_defer(...)`, and structured JSON `log_event(...)` with `level` gating via `LOG_LEVEL`.
- `roles.yaml`
  - Top-level `roles:` map; each role has `{ pattern: {O,C,E,A,N ∈ [-1,1]}, dept, desc }`.
- `validate_roles.py`
  - Enforces exact keys O,C,E,A,N, numeric weights in [-1,1]; fails fast with exit codes and prints clear errors.

## How to run (dev workflows)
- Local offline check (no Discord needed): `python main.py 105 90 95 83 60` prints role/desc/dept.
- Bot run expects token from `DISCORD_BOT_TOKEN` (or `DISCORD_BOT_TOKEN_FILE`). Optional: `DEV_GUILD_ID` for fast single-guild sync; `LOG_LEVEL` for logs.
- Docker: image published at `ghcr.io/iplaycomputer/personaocean:latest`; `docker run --env-file .env ...` or `docker compose up -d` (see `docs/OPS-CHEATSHEET.md`).
- Before changing role templates, run `python validate_roles.py` and ensure it passes.

## Patterns to follow (code conventions)
- New slash commands: decorate on `bot.tree` in `main.py`. For responses > ~1s, call `await maybe_defer(interaction)` early.
- Always send responses via `send_safe(...)` to avoid double-respond and handle rate limits; prefer ephemeral for private info.
- Emit structured logs with `log_event("cmd_<name>", ...)` and include `guild_id`, `user_id`, `duration_ms` where relevant. Respect `LOG_LEVEL`.
- Input validation mirrors existing commands: check ranges and friendly guards (e.g., reject “all 120s” case in `/ocean`).
- Keep state ephemeral and per-guild (`companies` dict). Don’t add persistence or cross-guild sharing without an explicit requirement.
- For formatted output, reuse the existing styles: simple text for concise, `discord.Embed` for detailed (see `/summary`).

## Integration points and env
- Dependencies pinned in `requirements.txt`: `discord.py`, `PyYAML`, `python-dotenv`.
- Env vars: `DISCORD_BOT_TOKEN` (or `DISCORD_BOT_TOKEN_FILE`), `LOG_LEVEL` (DEBUG|INFO|WARN|ERROR), `DEV_GUILD_ID` (optional single-guild sync).
- Slash command propagation: global sync can take up to an hour; for iteration, use `DEV_GUILD_ID`.

## Examples (copy these patterns)
- Reading roles: `roles = load_roles()` then `match_role(O,C,E,A,N)` returns `(role, desc, dept, score)`.
- Logging an action: `log_event("cmd_company", guild_id=..., user_id=..., members=len(registry), duration_ms=...)`.
- Safe send pattern: `await send_safe(interaction, content_or_embed, ephemeral=<bool>)`.

## Don’t do
- Don’t persist user data to disk/DB.
- Don’t change the shape of `roles.yaml` without updating `validate_roles.py` and `load_roles()`.
- Don’t bypass `send_safe`/`maybe_defer`; they encapsulate rate-limit and UX safeguards.

References: `README.md`, `docs/OPS-CHEATSHEET.md`, `docs/ops.md`, `docs/SCIENTIFIC_FRAMEWORK.txt`.