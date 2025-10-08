# PersonaOCEAN

A simple Discord bot that maps Big Five (OCEAN) scores to clear archetype roles and departments.

## Invite and use (for community admins)

[Invite PersonaOCEAN to your server](https://discord.com/oauth2/authorize?client_id=1425093192096678060&permissions=3072&scope=bot%20applications.commands)

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

## Quick Start

Run the prebuilt image from GHCR (Docker or Docker Desktop):

```powershell
docker run --rm -e DISCORD_BOT_TOKEN=YOUR_TOKEN ghcr.io/iplaycomputer/personaocean:latest
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

More docs: See `docs/OPS-CHEATSHEET.md` and `docs/ops.md`.

<!-- Contributing details moved to bottom minimal section -->

<!-- Duplicate Quick Start removed; see Quick Start above -->

## Contributing

PRs to `main` welcome. Before you push, run `python validate_roles.py`.
Optional: set `DEV_GUILD_ID` to sync slash commands to one guild for faster testing.

More docs: see `docs/OPS-CHEATSHEET.md` and `docs/ops.md`.

