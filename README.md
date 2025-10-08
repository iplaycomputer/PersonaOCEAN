# PersonaOCEAN

[![Release](https://img.shields.io/github/v/release/iplaycomputer/PersonaOCEAN)](https://github.com/iplaycomputer/PersonaOCEAN/releases)
[![Docker](https://img.shields.io/badge/Docker-ready-blue)](https://www.docker.com/)
[![License](https://img.shields.io/github/license/iplaycomputer/PersonaOCEAN)](LICENSE)

[![Validate Roles](https://github.com/iplaycomputer/PersonaOCEAN/actions/workflows/validate.yml/badge.svg)](https://github.com/iplaycomputer/PersonaOCEAN/actions/workflows/validate.yml)
[![Dependabot Status](https://img.shields.io/badge/Dependabot-enabled-brightgreen?logo=dependabot)](https://docs.github.com/code-security/dependabot)

A simple Discord bot that maps Big Five (OCEAN) scores to clear archetype roles and departments. Fast, clean, and grounded in a transparent YAML taxonomy.

## Invite and use (for community admins)

Ask the owner for the bot’s invite link, add it to your server, then use slash commands:

```text
/ocean O C E A N
```

Example:

```text
/ocean 105 90 95 83 60
```

The bot replies with the archetype and department.

See your server’s roster:

```text
/company
```

Need a reminder?

```text
/help
```

Delete your data from this server:

```text
/forget
```

Example roster reply:

```text
🏢 OnlyHorses Company Members:
- Kira: Visionary (Strategy & Management)
- BR: Guardian (Operations & Ethics)
```

Notes for admins:

- Use the slash commands picker; no prefix (!) needed.
- Scores should be 0–120; the bot normalizes them internally.
- Slash commands may take up to a minute to appear after the bot joins a new server.
- Privacy: PersonaOCEAN does not permanently store any data. All information is held in memory only and is erased when the bot restarts.

## What it does (at a glance)

- Normalizes OCEAN (0–120) to −1..+1
- Matches against a YAML-defined pattern per role
- Stores results per server (no cross-server sharing)
- Keeps everything in memory (resets on restart)

### How scoring works (simple math)

- Inputs are in the 0–120 range. The bot normalizes each to −1..+1 via (x − 60) / 60.
- Each role has a pattern vector (weights from −1.0 to +1.0) in `roles.yaml`.
- The match is a dot product: higher sum(trait × weight) → better fit.
- This stays readable and fast; no databases, z-scores, or facet-level math.

---

## For developers and self-hosters

Clone this repo if you want to host your own instance. Otherwise, skip this section.

### What’s included

- `roles.yaml` — Archetypes with O/C/E/A/N patterns, department, and description
- `main.py` — Discord bot (slash commands) and CLI fallback for quick local testing
- `requirements.txt` — Minimal dependencies
- `.gitignore` — Keeps virtualenv and secrets out of git
- `.env` (local) — Your bot token, auto-loaded (not committed)
- `validate_roles.py` — Validate roles.yaml structure and weight ranges before committing

### Repo file structure

```text
persona-ocean/
├── main.py
├── roles.yaml
├── requirements.txt
├── .env                 # your token (ignored by git)
└── .gitignore
```

### Self-host quick start (Windows PowerShell)

Prereqs: Python 3.9+ required and a bot token from [discord.com/developers](https://discord.com/developers)

Create a virtual environment and install dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Add your token:

```powershell
$env:DISCORD_BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
```

Or create `.env` (auto-loaded):

```dotenv
DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN
```

Run the bot:

```powershell
python .\main.py
```

Local CLI test (no Discord):

```powershell
python .\main.py 105 90 95 83 60
```

### Invite URL (owner-only)

After creating your application and adding a Bot user, generate an invite URL:

1. In the Developer Portal, copy your Client ID.
2. Build an OAuth2 URL with minimal perms and applications.commands scope:

```text
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=3072&scope=bot%20applications.commands
```

Notes:

- permissions=3072 grants Send Messages (2048) + Read Message History (1024). Adjust if needed.
- No Message Content intent required for slash commands.

Developer notes:

- Optional fast sync for testing: set DEV_GUILD_ID in your environment to sync commands to one server instantly.
- Validate YAML before deploy: run `python validate_roles.py` to check structure and weight ranges (see [`validate_roles.py`](validate_roles.py)).

## Contributing

All contributions must go through pull requests targeting the `main` branch.
Pull requests are automatically validated by the `Validate Roles` workflow.
Please ensure `roles.yaml` passes validation before requesting review.

Maintainer: [@iplaycomputer](https://github.com/iplaycomputer)

Contributions are welcome! To keep things clean and consistent:

1. Validate YAML before pushing:

```bash
python validate_roles.py
```

1. Run pre-commit locally to auto-fix formatting:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

1. CI checks — every push and PR automatically runs the Validate Roles workflow on GitHub Actions.

For release notes and roadmap, see [CHANGELOG.md](CHANGELOG.md).

## Scientific references

PersonaOCEAN aims to be transparent and grounded. The role taxonomy, matching math, and team-level indicators are designed to be readable and auditable.

- Read the full citation backbone and implementation notes: [docs/SCIENTIFIC_FRAMEWORK.txt](docs/SCIENTIFIC_FRAMEWORK.txt)
- Highlights:
  - Big Five foundations and measurement references
  - Personality in teams and team performance meta-analyses
  - Non-linear (inverted-U) effects and the Too-Much-of-a-Good-Thing (TMGT) literature
  - Person–environment fit references and practical cautions
  - A plain-language section on how PersonaOCEAN applies these ideas

Limitations and ethics: This tool is for exploration and discussion. It is not a clinical instrument and shouldn’t be used for high-stakes decisions (e.g., hiring/promotion) without proper validation and oversight. Data are kept in memory per server and not persisted.

🔍 Verification: All key sources verified and DOIs audited.
See `docs/VERIFICATION_AUDIT_v1.1.txt` for the full verification report.

## 📖 Citation

If you use PersonaOCEAN in research, teaching, or applied projects, please cite:

**PersonaOCEAN Project (2025).**  
*PersonaOCEAN: An Open-Source Psychometric Framework for Team Personality Analysis.*  
Version 1.1.2 — DOI Integration.  
GitHub: [https://github.com/iplaycomputer/PersonaOCEAN](https://github.com/iplaycomputer/PersonaOCEAN)  
DOI: 10.5281/zenodo.17289322

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17289322.svg)](https://doi.org/10.5281/zenodo.17289322)

---
This citation ensures proper credit and reproducibility for derivative research.

### Copy-paste citation examples

BibTeX

```bibtex
@software{PersonaOCEAN_zenodo_17289322,
  author    = {PersonaOCEAN Project},
  title     = {PersonaOCEAN: An Open-Source Psychometric Framework for Team Personality Analysis},
  version   = {1.1.2},
  date      = {2025-10-07},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.17289322},
  url       = {https://doi.org/10.5281/zenodo.17289322},
  license   = {MIT}
}
```

APA (7th)

PersonaOCEAN Project. (2025). PersonaOCEAN: An Open-Source Psychometric Framework for Team Personality Analysis (Version 1.1.2) [Computer software]. Zenodo. [https://doi.org/10.5281/zenodo.17289322](https://doi.org/10.5281/zenodo.17289322)

---

## Operations (logging)

PersonaOCEAN emits structured, JSON-like logs to stdout so you can trace behavior during load tests and production.

- Key fields:
  - `event`: Short event name (e.g., `interaction_deferred`, `cmd_summary`, `cmd_error`).
  - `guild_id`, `user_id`: Context for where/who triggered the action.
  - Command metrics: `members`, `teamwork_index`, `duration_ms` (elapsed milliseconds), etc.
  - `traceback`: Present only on `cmd_error` for quick diagnostics.

- Verbosity: Set `LOG_LEVEL=DEBUG` (or `INFO`/`WARNING`/`ERROR`) in your environment to adjust noise.

- Example log line:

```json
{"ts":"2025-10-07T17:24:10Z","event":"cmd_summary","guild_id":1234567890,"user_id":111222333,"detailed":true,"members":7,"teamwork_index":0.892,"duration_ms":214}
```

Tip: Pipe logs to a file or collector (e.g., `jq`/ELK) to filter by `event` or investigate latency (`duration_ms`).

For a deeper operations playbook (jq filters, Windows PowerShell equivalents, alert ideas), see: [docs/ops.md](docs/ops.md).

### Run with Docker (optional)

You can run PersonaOCEAN as a container. Structured logs are printed to stdout.

Windows PowerShell example:

```powershell
# Build image
docker build -t personaocean:local .

# Run container with env vars
$env:DISCORD_BOT_TOKEN = "YOUR_TOKEN"; $env:LOG_LEVEL = "INFO"
docker run --rm -it --name personaocean `
  -e DISCORD_BOT_TOKEN=`"$env:DISCORD_BOT_TOKEN`" `
  -e LOG_LEVEL=`"$env:LOG_LEVEL`" `
  personaocean:local

# Or using Docker Compose
$env:DISCORD_BOT_TOKEN = "YOUR_TOKEN"; $env:LOG_LEVEL = "INFO"
docker compose up --build
```

The provided `docker-compose.yml` uses `restart: always` and JSON-file log rotation (10MB x 3 files).

