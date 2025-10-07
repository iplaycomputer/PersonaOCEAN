# v1.1.0 — Curșeu Integration & Transparency Update

## What’s new

- Teamwork Fit in `/summary detailed:true`
  - Uses an inverted-U approximation based on Curșeu et al. (2018) for Extraversion, Agreeableness, and Conscientiousness, with small, transparent adjustments for Stability (low Neuroticism) and balanced Openness.
- Scientific transparency
  - Added `docs/SCIENTIFIC_FRAMEWORK.txt` with complete citations and a plain-language “How PersonaOCEAN uses this research” explainer.
  - README now includes a “Scientific references” section and an ethics note.
- Discoverability in Discord
  - New `/about` command linking directly to README and Scientific Framework.
  - Detailed summary embed footer cites Curșeu et al. (2018).

## Why it matters

- Builds trust by making the math and sources visible and easy to audit.
- Encourages nuanced, non-binary interpretation of team traits via an inverted-U model.
- Keeps Discord UX clean while making references discoverable in one click.

## Upgrade notes

- No breaking changes.
- Optional: set `DEV_GUILD_ID` to your test server for instant slash-command sync; global sync may take time to propagate.

## Acknowledgments

- Curșeu, P. L., Ilies, R., Vîrgă, D., Maricuţoiu, L., & Sava, F. A. (2018). Personality characteristics that are valued in teams: Not always “more is better.” International Journal of Psychology, 54(5), 638–649.
