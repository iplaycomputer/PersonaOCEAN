# Operations Guide

This guide shows how to work with the bot's structured JSON logs and quickly filter common events.

## Log anatomy

Each line is a single JSON object. Core fields:

- event: short event name (e.g., cmd_summary, cmd_error, interaction_deferred)
- ts: ISO 8601 timestamp
- guild_id, channel_id, user_id
- cmd: command name (if applicable)
- duration_ms: elapsed time for the action
- level: log level (DEBUG/INFO/WARN/ERROR)

The log level is controlled by the environment variable `LOG_LEVEL` (default: INFO).

## Quick filters with jq (Linux/macOS)

- Only errors:
  jq 'select(.level=="ERROR")'

- Only command errors:
  jq 'select(.event=="cmd_error")'

- Only from a specific guild:
  jq 'select(.guild_id=="123456789012345678")'

- Slow commands (> 1500 ms):
  jq 'select(.duration_ms != null and .duration_ms > 1500) | {ts,event,cmd,duration_ms,guild_id}'

- Summary of error counts by event:
  jq -r 'select(.level=="ERROR") | .event' | sort | uniq -c | sort -nr

- Inspect top 10 slowest cmd_summary events (most recent logs first):
  tac bot.log | jq 'select(.event=="cmd_summary" and .duration_ms!=null) | [.duration_ms,.ts,.user_id] | @tsv' | head -n 2000 | sort -nr | head -n 10

Note: `tac` may not be available on macOS by default. You can use `tail -r` instead.

## PowerShell equivalents (Windows)

Assuming logs are in `bot.log`.

- Only errors:
  Get-Content bot.log | ForEach-Object { $_ | ConvertFrom-Json } | Where-Object { $_.level -eq 'ERROR' }

- Only command errors:
  Get-Content bot.log | ForEach-Object { $_ | ConvertFrom-Json } | Where-Object { $_.event -eq 'cmd_error' }

- Only from a specific guild:
  $G='123456789012345678'; Get-Content bot.log | % { $_ | ConvertFrom-Json } | ? { $_.guild_id -eq $G }

- Slow commands (> 1500 ms):
  Get-Content bot.log | % { $_ | ConvertFrom-Json } | ? { $_.duration_ms -gt 1500 } | Select-Object ts, event, cmd, duration_ms, guild_id

- Count errors by event:
  Get-Content bot.log | % { $_ | ConvertFrom-Json } | ? { $_.level -eq 'ERROR' } | Group-Object event | Sort-Object Count -Descending | Select-Object Count, Name

- Top 10 slowest cmd_summary events (approx):
  Get-Content bot.log | % { $_ | ConvertFrom-Json } | ? { $_.event -eq 'cmd_summary' -and $_.duration_ms } | Sort-Object duration_ms -Descending | Select-Object -First 10 ts, user_id, duration_ms

Tips:

- For live logs: `Get-Content bot.log -Wait`
- You can pipe from process output if your hosting platform streams stdout directly.

## Rotating logs

If you write logs to a file, consider rotation to keep size manageable. For systemd, use journal settings; for Docker, use `--log-opt max-size` and `--log-opt max-file`.

## Alerts and thresholds

Useful alert ideas:

- Spike in cmd_error or send_error events
- Sustained increase in defer_failed
- Median cmd_summary duration_ms over 2s
- 5xx HTTPException rate from Discord API

## Environment variables

- LOG_LEVEL: DEBUG/INFO/WARN/ERROR (default: INFO)
- DISCORD_TOKEN: Bot token
- (optional) GUILD_ID_ALLOWLIST: comma-separated list of guild IDs to allow (for staged rollouts)

