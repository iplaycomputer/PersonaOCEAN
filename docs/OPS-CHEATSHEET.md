# PersonaOCEAN — Ops cheat sheet

Quick reference for running, updating, and troubleshooting.

## Start / Stop / Restart (Docker Compose)

Windows PowerShell examples:

```powershell
# Start (reads .env automatically)
docker compose up -d

# Follow logs (JSON)
docker compose logs -f bot

# Stop
docker compose down

# Restart
docker compose down ; docker compose up -d
```

Tip: You can start and stop the bot from Docker Desktop → Containers → personaocean → Start / Stop.

## Update to latest image (GHCR)

```powershell
docker pull ghcr.io/iplaycomputer/personaocean:latest
docker compose down ; docker compose up -d --force-recreate
```

To pin to a specific version, replace `latest` with a tag (e.g., `v1.2.1`).

## Logs — quick filters

Linux/macOS:

```bash
docker compose logs -f bot | jq 'select(.level=="ERROR")'
```

Windows PowerShell (skip non-JSON lines safely):

```powershell
docker compose logs -f bot | % { try { $_ | ConvertFrom-Json } catch { $null } } | ? { $_ -and $_.level -eq 'ERROR' }
```

More filters and examples: see docs/ops.md

## Recovery

- If something looks off, check logs for `cmd_error`, `send_error`, or `defer_failed`.
- Clean restart fixes most transient issues: `docker compose down ; docker compose up -d`

## Token management

- Put DISCORD_BOT_TOKEN in your environment (or `.env` for compose)
- Rotate the token if leaked; then restart the container
