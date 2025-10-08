# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] — 2025-10-08

### Added

- Minimal Dockerfile and docker-compose setup
- Structured JSON logging with log levels
- Graceful shutdown and HEALTHCHECK
- Ops docs: Docker log filters (jq, PowerShell) and troubleshooting tips

### Improved

- Markdown lint and formatting in documentation

For prior verification work and scientific framework details, see docs/VERIFICATION_AUDIT_v1.1.txt and docs/SCIENTIFIC_FRAMEWORK.txt.
# Changelog

## v1.1.0 – Curșeu Integration & Transparency Update (2025-10-07)

### Added

- Teamwork Fit index in `/summary detailed:true`, inspired by Curșeu et al. (2018) inverted-U moderation of teamwork-relevant traits (E, A, C) with small adjustments for stability and balanced openness.
- Scientific Framework document with complete citation backbone and a plain-language explainer: `docs/SCIENTIFIC_FRAMEWORK.txt`.
- New `/about` command linking to the README and Scientific Framework; includes a short ethics note.
- Research attribution footer in the detailed summary embed.

### Changed

- README now includes a “Scientific references” section linking to the framework and clarifying limitations/ethics.

### Notes

- No breaking changes. Slash-command sync is instant when `DEV_GUILD_ID` is set; global sync can take time to propagate.

## v1.0.0 – Initial public release

- Added /ocean, /company, /help, /forget commands
- Added per-guild isolation and YAML role taxonomy
- Added validate_roles.py + CI hooks
- Privacy compliant and slash-command aligned
