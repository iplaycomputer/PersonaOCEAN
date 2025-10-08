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

## Health & recovery

- Health: container is marked healthy when its heartbeat file is fresh (~30s cadence)
- Heartbeat is stored in `/tmp` (tmpfs) to keep the root filesystem read-only.
- If `unhealthy`, check recent `cmd_error`, `send_error`, `defer_failed` in logs
- Clean restart fixes most transient issues: `docker compose down ; docker compose up -d`

## Token management

- Local dev: put DISCORD_BOT_TOKEN in `.env` (not committed)
- Production: use a file-backed secret and set `DISCORD_BOT_TOKEN_FILE=/run/secrets/discord_bot_token`
- Rotate the token monthly or if leaked; then restart the container

## Re-tag and release (maintainer)

```bash
git tag -a vX.Y.Z -m "vX.Y.Z — release notes"
git push origin vX.Y.Z
# CI will build/push Docker image and publish the GitHub Release automatically
```

## Quick sanity checklist

- Slash commands respond within Discord (~instant after dev sync, slower globally)
- Logs show `cmd_summary`, `cmd_error`, etc. with proper `level`
- Health check transitions to healthy within ~1 minute of start
- Branch protection only requires live checks (no stale "Expected")
