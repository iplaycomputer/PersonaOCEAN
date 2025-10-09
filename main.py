import os
import sys
import time
import json
import traceback
import yaml
import discord
from dotenv import load_dotenv
from collections import Counter
from typing import Optional

# Optional facet support scaffolding (non-breaking)
try:
    from persona.facets import normalize_facets_payload  # type: ignore
except Exception:
    normalize_facets_payload = None  # gracefully absent if module not present

# Preview limits / knobs
MAX_PREVIEW_FACETS = 8

# --- Load roles ---
def load_roles(path: str = "roles.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if not data or "roles" not in data:
            raise ValueError("roles.yaml missing 'roles' key")
        return data["roles"]

roles = load_roles()

# --- Normalize and match ---
# convert 0–120 to -1..+1

def normalize(val: float) -> float:
    return (val - 60.0) / 60.0


def match_role(O: float, C: float, E: float, A: float, N: float):
    traits = {
        "O": normalize(O),
        "C": normalize(C),
        "E": normalize(E),
        "A": normalize(A),
        "N": normalize(N),
    }
    best_role, best_score = None, float("-inf")
    for name, data in roles.items():
        pattern = data["pattern"]
        # dot product similarity
        score = sum(traits[t] * float(pattern[t]) for t in pattern)
        if score > best_score:
            best_role = name
            best_score = score
    if best_role is None:
        raise ValueError("No roles found or roles.yaml pattern is invalid")
    r = roles[best_role]
    return best_role, r["desc"], r["dept"], best_score


# --- Discord setup ---
# Load environment from .env if present
load_dotenv()

# Intents: message content not required for slash commands
intents = discord.Intents.default()
# Explicit for clarity (defaults already include guilds)
intents.guilds = True
# intents.members = True  # optional if you later need full member cache

# --- In-memory per-guild registry ---
# {guild_id: {user_id: {traits: {O,C,E,A,N}, role: str, dept: str}}}
companies: dict[int, dict[int, dict]] = {}


class OceanBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        # Fast dev sync: set DEV_GUILD_ID in env to register commands to one guild
        dev_guild_id = os.getenv("DEV_GUILD_ID")
        if dev_guild_id:
            guild = discord.Object(id=int(dev_guild_id))
            await self.tree.sync(guild=guild)
            print(f"✅ Slash commands synced to guild {dev_guild_id}")
        else:
            # Global sync (may take up to 1 hour to propagate)
            await self.tree.sync()
            print("✅ Slash commands synced globally")

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")


bot = OceanBot(intents=intents)


# --- Helper: safe send with basic rate-limit handling ---
async def send_safe(interaction: discord.Interaction, content: str = None, *, embed: discord.Embed = None, ephemeral: bool = False):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
    except (discord.HTTPException, discord.NotFound) as e:
        try:
            msg = "⚠️ Rate limited, please try again."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass
        log_event(
            "send_error",
            level="WARN",
            error=str(e),
            guild_id=getattr(interaction.guild, "id", None),
            user_id=getattr(interaction.user, "id", None),
            channel_id=getattr(getattr(interaction, "channel", None), "id", None),
        )


# --- Logging utilities ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LEVEL_ORDER = {"DEBUG": 10, "INFO": 20, "WARN": 30, "WARNING": 30, "ERROR": 40}

def _norm_level(level: str) -> str:
    lvl = (level or "INFO").upper()
    return "WARN" if lvl == "WARNING" else lvl

def _level_ok(level: str) -> bool:
    return LEVEL_ORDER.get(_norm_level(level), 20) >= LEVEL_ORDER.get(_norm_level(LOG_LEVEL), 20)

def log_event(event: str, *, level: str = "INFO", **kwargs):
    # Honor LOG_LEVEL and include a level field in the record
    if not _level_ok(level):
        return
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        "level": _norm_level(level),
        **kwargs,
    }
    try:
        print(json.dumps(record, ensure_ascii=False))
    except Exception:
        print(f"{record}")


async def maybe_defer(interaction: discord.Interaction, *, ephemeral: bool = False):
    """Defer the interaction if not already responded, extending the 3s window.
    Use for longer-running commands (~>1s) to avoid 'Unknown interaction' errors.
    """
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True, ephemeral=ephemeral)
            log_event(
                "interaction_deferred",
                level="INFO",
                guild_id=getattr(interaction.guild, "id", None),
                user_id=getattr(interaction.user, "id", None),
                channel_id=getattr(getattr(interaction, "channel", None), "id", None),
                cmd=getattr(interaction.command, "name", None),
            )
    except discord.HTTPException as e:
        log_event(
            "defer_failed",
            level="WARN",
            error=str(e),
            cmd=getattr(interaction.command, "name", None),
            guild_id=getattr(interaction.guild, "id", None),
            user_id=getattr(interaction.user, "id", None),
            channel_id=getattr(getattr(interaction, "channel", None), "id", None),
        )


@bot.tree.command(name="ocean", description="Get your archetype from OCEAN scores (0–120 each)")
@discord.app_commands.describe(
    o="Openness (0–120)",
    c="Conscientiousness (0–120)",
    e="Extraversion (0–120)",
    a="Agreeableness (0–120)",
    n="Neuroticism (0–120)",
)
async def ocean_command(
    interaction: discord.Interaction,
    o: int,
    c: int,
    e: int,
    a: int,
    n: int,
):
    # Validate input ranges
    scores = {"O": o, "C": c, "E": e, "A": a, "N": n}
    invalid = [trait for trait, score in scores.items() if not (0 <= score <= 120)]
    if invalid:
        await send_safe(
            interaction,
            f"⚠️ Invalid scores: {', '.join(invalid)}. Scores must be between 0 and 120.",
            ephemeral=True,
        )
        log_event(
            "invalid_input",
            level="WARN",
            guild_id=getattr(interaction.guild, "id", None),
            user_id=getattr(interaction.user, "id", None),
            invalid_traits=invalid,
        )
        return

    # Friendly guard for the extreme "all 120s" case
    if all(v == 120 for v in scores.values()):
        await send_safe(
            interaction,
            "🤔 All 120s? TOO STRONG, BUDDY! Please enter real scores between 0 and 120 from a Big Five test.",
            ephemeral=True,
        )
        log_event(
            "extreme_input",
            level="WARN",
            guild_id=getattr(interaction.guild, "id", None),
            user_id=getattr(interaction.user, "id", None),
        )
        return

    role, desc, dept, _ = match_role(float(o), float(c), float(e), float(a), float(n))
    guild = interaction.guild
    guild_id = guild.id if guild else None
    if guild_id is not None:
        if guild_id not in companies:
            companies[guild_id] = {}
        companies[guild_id][interaction.user.id] = {
            "traits": {"O": o, "C": c, "E": e, "A": a, "N": n},
            "role": role,
            "dept": dept,
        }
    stored_line = f"\n🗂️ Stored in company: `{guild.name}`" if guild_id is not None else ""
    await send_safe(
        interaction,
        f"🎭 **{role}** — {desc}\n🏢 Department: *{dept}*{stored_line}",
        ephemeral=False,
    )


@bot.tree.command(name="company", description="List members registered in this server (company)")
async def company_command(interaction: discord.Interaction):
    start = time.perf_counter()
    guild = interaction.guild
    guild_id = guild.id if guild else None
    if guild_id is None:
        await send_safe(interaction, "🏢 This command can only be used in a server.", ephemeral=True)
        return
    # This may iterate many members; defer to avoid 3s timeout under load
    await maybe_defer(interaction, ephemeral=False)
    registry = companies.get(guild_id, {})
    if not registry:
        await send_safe(interaction, "🏢 No members registered yet in this company.", ephemeral=True)
        return
    lines = []
    for uid, data in registry.items():
        member = guild.get_member(uid)
        if member is None:
            try:
                member = await guild.fetch_member(uid)
            except Exception:
                member = None
        display = member.display_name if member else f"Unknown User ({uid})"
        lines.append(f"- {display}: {data['role']} ({data['dept']})")
    await send_safe(interaction, f"🏢 **{guild.name} Company Members:**\n" + "\n".join(lines), ephemeral=False)
    log_event(
        "cmd_company",
        guild_id=guild_id,
        user_id=getattr(interaction.user, "id", None),
        members=len(registry),
        duration_ms=int((time.perf_counter() - start) * 1000),
    )


@bot.tree.command(name="departments", description="List company members by department")
async def departments_command(interaction: discord.Interaction):
    start = time.perf_counter()
    guild = interaction.guild
    guild_id = guild.id if guild else None
    if guild_id is None:
        await send_safe(interaction, "🏢 This command can only be used in a server.", ephemeral=True)
        return

    registry = companies.get(guild_id, {})
    if not registry:
        await send_safe(interaction, "🏢 No members registered yet in this company.", ephemeral=True)
        return

    # Defer early for potentially heavy grouping/formatting
    await maybe_defer(interaction, ephemeral=False)

    # Group members by department
    depts: dict[str, list[str]] = {}
    for uid, data in registry.items():
        dept = data["dept"]
        member = guild.get_member(uid)
        if member is None:
            try:
                member = await guild.fetch_member(uid)
            except Exception:
                member = None
        name = member.display_name if member else f"Unknown User ({uid})"
        depts.setdefault(dept, []).append(f"{name} — {data['role']}")

    # Format
    lines = [f"🏢 **{guild.name} — Departments:**"]
    for dept, members in depts.items():
        lines.append(f"\n**{dept}:**")
        for m in members:
            lines.append(f"- {m}")

    await send_safe(interaction, "\n".join(lines), ephemeral=False)
    log_event(
        "cmd_departments",
        guild_id=guild_id,
        user_id=getattr(interaction.user, "id", None),
        dept_count=len(depts),
        duration_ms=int((time.perf_counter() - start) * 1000),
    )


@bot.tree.command(name="profile", description="See your stored archetype and OCEAN scores")
async def profile_command(interaction: discord.Interaction):
    guild = interaction.guild
    guild_id = guild.id if guild else None
    if guild_id is None:
        await send_safe(interaction, "🏢 This command can only be used in a server.", ephemeral=True)
        return

    registry = companies.get(guild_id, {})
    user_data = registry.get(interaction.user.id)
    if not user_data:
        await send_safe(interaction, "You don't have a profile yet. Run `/ocean` first to get your archetype!", ephemeral=True)
        return

    t = user_data["traits"]
    msg = (
        f"🎭 **{interaction.user.display_name} — {user_data['role']}**\n"
        f"🏢 Department: *{user_data['dept']}*\n"
        f"O: {t['O']} | C: {t['C']} | E: {t['E']} | A: {t['A']} | N: {t['N']}"
    )
    await send_safe(interaction, msg, ephemeral=True)


@bot.tree.command(name="summary", description="See a quick company-wide archetype summary")
@discord.app_commands.describe(mode="Choose 'concise' or 'detailed' output")
@discord.app_commands.choices(
    mode=[
        discord.app_commands.Choice(name="Concise", value="concise"),
        discord.app_commands.Choice(name="Detailed", value="detailed"),
    ]
)
async def summary_command(interaction: discord.Interaction, mode: Optional[str] = None):
    start = time.perf_counter()
    is_detailed = (mode == "detailed")
    guild = interaction.guild
    guild_id = guild.id if guild else None
    if guild_id is None:
        await send_safe(interaction, "🏢 This command can only be used in a server.", ephemeral=True)
        return

    registry = companies.get(guild_id, {})
    if not registry:
        await send_safe(interaction, "🏢 No members registered yet in this company.", ephemeral=True)
        return

    # Defer for heavier aggregation & embed construction
    await maybe_defer(interaction, ephemeral=False)

    # Count totals
    total = len(registry)
    dept_counts = Counter(data["dept"] for data in registry.values())
    role_counts = Counter(data["role"] for data in registry.values())
    top_roles = ", ".join(r for r, _ in role_counts.most_common(3))

    # Format department counts
    depts_text = "\n".join([f"- {dept}: {count}" for dept, count in dept_counts.items()])

    # --- Compute average OCEAN for fun insight ---
    trait_sums = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    for data in registry.values():
        for t in trait_sums:
            trait_sums[t] += data["traits"][t]
    avg_traits = {t: trait_sums[t] / total for t in trait_sums}
    norm = {t: (avg_traits[t] - 60) / 60 for t in avg_traits}

    # Rank traits
    sorted_traits = sorted(norm.items(), key=lambda kv: kv[1], reverse=True)
    top_trait, top_val = sorted_traits[0]
    bottom_trait, bottom_val = sorted_traits[-1]

    def describe_trait(t):
        return {
            "O": "curious and imaginative 🎨",
            "C": "organized and goal-driven 📋",
            "E": "outgoing and energetic ⚡",
            "A": "cooperative and kind 💛",
            "N": "emotionally intense 🌊",
        }[t]

    # --- Teamwork Index (Curșeu et al. 2018) ---
    def teamwork_value(trait_score):
        """Inverted U-curve: moderate levels optimal for teamwork"""
        x = trait_score / 120
        # Peak at 0.5, drop symmetrically toward 0 and 1
        return 1 - 4 * (x - 0.5)**2

    # Compute teamwork index for E, A, C (inverted U) + stability/openness bonuses
    e_avg = sum(data["traits"]["E"] for data in registry.values()) / total
    a_avg = sum(data["traits"]["A"] for data in registry.values()) / total
    c_avg = sum(data["traits"]["C"] for data in registry.values()) / total
    o_avg = sum(data["traits"]["O"] for data in registry.values()) / total
    n_avg = sum(data["traits"]["N"] for data in registry.values()) / total

    teamwork_index = (
        teamwork_value(e_avg) +
        teamwork_value(a_avg) + 
        teamwork_value(c_avg)
    ) / 3

    # Add emotional stability bonus (low N) and moderate O bonus
    teamwork_index += 0.1 * ((120 - n_avg) / 120)  # Emotional stability boost
    teamwork_index += 0.05 * (1 - abs((o_avg / 120) - 0.5) * 2)  # Mid-range O bonus
    
    # Clamp to [0, 1]
    teamwork_index = max(0, min(1, teamwork_index))

    # Teamwork interpretation
    if teamwork_index >= 0.80:
        teamwork_label = "Highly Synergistic 🤝"
    elif teamwork_index >= 0.60:
        teamwork_label = "Collaborative Potential 🌱"
    elif teamwork_index >= 0.40:
        teamwork_label = "Imbalanced ⚖️"
    else:
        teamwork_label = "Team Disruptor ⚡"

    # --- Fun vibe tiers ---
    avg_spread = top_val - bottom_val
    if avg_spread < 0.3:
        vibe_line = "A harmonious blend ⚖️ — balanced across personalities."
    elif top_val > 0.6 and bottom_val < -0.4:
        vibe_line = f"Bold innovators 🚀 — strongly {describe_trait(top_trait)} and low in {bottom_trait}."
    elif top_val > 0.5:
        vibe_line = f"This company leans {describe_trait(top_trait)}."
    elif bottom_val < -0.5:
        vibe_line = f"Grounded and steady 🌱 — low in {bottom_trait}."
    else:
        vibe_line = "A well-rounded team with complementary strengths 🔄."

    # Optional detailed OCEAN bar chart
    def make_bar(value):
        # map -1..+1 → 0..5 filled blocks
        filled = int((value + 1) * 2.5)
        return "█" * filled + "░" * (5 - filled)

    if is_detailed:
        # Professional embed for detailed view
        embed = discord.Embed(
            title=f"🏢 {guild.name} — Company Summary",
            description=f"👥 **Members:** {total}\n✨ *{vibe_line}*",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Departments", value=depts_text or "—", inline=False)
        embed.add_field(name="Top Roles", value=top_roles or "—", inline=False)

        embed.add_field(
            name="Average OCEAN Profile",
            value="\n".join([
                f"{t}: {make_bar(norm[t])} ({norm[t]:+.2f})"
                for t in ["O", "C", "E", "A", "N"]
            ]),
            inline=False
        )
        
        sorted_avg = sorted(norm.items(), key=lambda kv: kv[1], reverse=True)
        dominant, dom_val = sorted_avg[0]
        weakest, weak_val = sorted_avg[-1]

        def label_trait(t):
            return {
                "O": "Openness",
                "C": "Conscientiousness", 
                "E": "Extraversion",
                "A": "Agreeableness",
                "N": "Neuroticism",
            }[t]

        embed.add_field(
            name="Team Balance",
            value=f"🧭 {label_trait(dominant)} dominant, {label_trait(weakest)} low.",
            inline=False
        )
        embed.add_field(
            name="Teamwork Fit",
            value=f"🤝 {teamwork_index:.2f} — {teamwork_label}",
            inline=False
        )

        # Research note footer for transparency
        embed.set_footer(text="Teamwork Fit uses moderate-trait weighting (Curșeu et al., 2018). See docs/SCIENTIFIC_FRAMEWORK.txt")

        await send_safe(interaction, embed=embed, ephemeral=False)
    else:
        # Simple text output for basic view
        msg = (
            f"🏢 **{guild.name} — Company Summary**\n"
            f"👥 Members: {total}\n\n"
            f"**Departments:**\n{depts_text}\n\n"
            f"**Top Roles:** {top_roles or '—'}\n\n"
            f"✨ *{vibe_line}*"
        )
        await send_safe(interaction, msg, ephemeral=False)

    log_event(
        "cmd_summary",
        guild_id=guild_id,
        user_id=getattr(interaction.user, "id", None),
        detailed=is_detailed,
        members=total,
        teamwork_index=round(teamwork_index, 3),
        duration_ms=int((time.perf_counter() - start) * 1000),
    )


@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    lines = [
        "Commands:",
        "/ocean o c e a n — five numbers (0–120) to get your archetype and department.",
        "/profile — view your current archetype and OCEAN scores.",
        "/company — list members registered in this server (company).",
        "/departments — list members grouped by department.",
        "/summary — view company-wide summary (add 'mode: Detailed' for charts).",
        "/forget — delete your stored data from this server.",
        "/about — learn about the project and references.",
    ]
    await send_safe(interaction, "\n".join(lines), ephemeral=True)
    log_event("cmd_help", guild_id=getattr(interaction.guild, "id", None), user_id=getattr(interaction.user, "id", None))


@bot.tree.command(name="about", description="About PersonaOCEAN and scientific references")
@discord.app_commands.checks.cooldown(1, 10.0)
async def about_command(interaction: discord.Interaction):
    repo_url = "https://github.com/iplaycomputer/PersonaOCEAN"
    docs_path = "docs/SCIENTIFIC_FRAMEWORK.txt"
    msg = (
        "PersonaOCEAN — a transparent OCEAN-to-archetype mapper with team insights.\n\n"
        "Key links:\n"
        f"• README: {repo_url}#readme\n"
        f"• Scientific Framework: {repo_url}/blob/main/{docs_path}\n\n"
        "Notes: Uses linear normalization, dot-product role matching, and a teamwork index inspired by Curșeu et al. (2018).\n"
        "Ethics: For exploration only — not for high-stakes decisions."
    )
    await send_safe(interaction, msg, ephemeral=True)
    log_event("cmd_about", guild_id=getattr(interaction.guild, "id", None), user_id=getattr(interaction.user, "id", None))


@bot.tree.command(name="forget", description="Delete your stored OCEAN data from this server")
async def forget_command(interaction: discord.Interaction):
    guild = interaction.guild
    guild_id = guild.id if guild else None
    if guild_id is None:
        await send_safe(interaction, "This command can only be used in a server.", ephemeral=True)
        return
    registry = companies.get(guild_id, {})
    removed = registry.pop(interaction.user.id, None)
    if removed is None:
        await send_safe(interaction, "No stored data found for you in this server.", ephemeral=True)
    else:
        await send_safe(interaction, "Your stored data has been deleted for this server.", ephemeral=True)
    log_event("cmd_forget", guild_id=guild_id, user_id=getattr(interaction.user, "id", None), removed=bool(removed))


@bot.tree.command(name="import_json", description="Import Big Five test results (JSON from bigfive-web). [Preview only]")
async def import_json_command(interaction: discord.Interaction, attachment: discord.Attachment):
    """Skeleton importer. Reads attached JSON and previews normalized facets.
    Non-breaking: does not mutate state yet. Uses existing safe-send and logging.
    """
    start = time.perf_counter()
    await maybe_defer(interaction, ephemeral=True)
    if normalize_facets_payload is None:
        await send_safe(
            interaction,
            "Facet import not enabled in this build. Please ensure persona/facets.py is available.",
            ephemeral=True,
        )
        log_event(
            "cmd_import_json_disabled",
            level="WARN",
            guild_id=getattr(interaction.guild, "id", None),
            user_id=getattr(interaction.user, "id", None),
        )
        return
    try:
        raw_bytes = await attachment.read()
        data = json.loads(raw_bytes.decode("utf-8"))
        facets = normalize_facets_payload(data)
        shown = ", ".join(list(facets.keys())[:MAX_PREVIEW_FACETS]) or "(none)"
        await send_safe(
            interaction,
            f"Imported JSON parsed. Example facets: {shown}\nNote: This is a preview; no data stored.",
            ephemeral=True,
        )
        log_event(
            "cmd_import_json",
            guild_id=getattr(interaction.guild, "id", None),
            user_id=getattr(interaction.user, "id", None),
            facet_count=len(facets),
            duration_ms=int((time.perf_counter() - start) * 1000),
        )
    except Exception as e:
        await send_safe(interaction, "Failed to parse the attached JSON.", ephemeral=True)
        log_event(
            "cmd_import_json_error",
            level="ERROR",
            guild_id=getattr(interaction.guild, "id", None),
            user_id=getattr(interaction.user, "id", None),
            error=str(e),
            duration_ms=int((time.perf_counter() - start) * 1000),
        )


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    # Friendly cooldown feedback takes precedence
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        try:
            await send_safe(
                interaction,
                f"⏳ You're going too fast. Try again in {error.retry_after:.1f}s.",
                ephemeral=True,
            )
        except Exception:
            pass
        log_event(
            "cooldown_hit",
            level="INFO",
            guild_id=getattr(interaction.guild, "id", None),
            user_id=getattr(interaction.user, "id", None),
            channel_id=getattr(getattr(interaction, "channel", None), "id", None),
            cmd=getattr(interaction.command, "name", None),
            retry_after=round(getattr(error, "retry_after", 0.0), 3),
        )
        return
    try:
        msg = "⚠️ Something went wrong. Please try again."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass
    log_event(
        "cmd_error",
        level="ERROR",
        guild_id=getattr(interaction.guild, "id", None),
        user_id=getattr(interaction.user, "id", None),
        channel_id=getattr(getattr(interaction, "channel", None), "id", None),
        cmd=getattr(interaction.command, "name", None),
        error=str(error),
        traceback="\n".join(traceback.format_exception(type(error), error, error.__traceback__)),
    )


def run_discord():
    # Prefer env var, then file path (for Docker secrets), then legacy var
    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("YOUR_DISCORD_BOT_TOKEN")
    if not token:
        token_file = os.getenv("DISCORD_BOT_TOKEN_FILE") or "/run/secrets/discord_bot_token"
        try:
            if os.path.isfile(token_file):
                with open(token_file, "r", encoding="utf-8") as f:
                    token = f.read().strip()
        except Exception:
            token = None
    if not token:
        print(
            "❌ Missing Discord token. Provide one of the following:"\
            "\n  - Set DISCORD_BOT_TOKEN in your environment or .env file"\
            "\n  - Or set DISCORD_BOT_TOKEN_FILE to a file containing the token"\
            "\n  - Or provide a Docker secret at /run/secrets/discord_bot_token"\
            "\n\nExample .env line:\nDISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN\n"\
            "# Or reference a file:\n# DISCORD_BOT_TOKEN_FILE=/run/secrets/discord_bot_token\n\n"\
            "Tip: For a quick local test without Discord, run: python main.py 105 90 95 83 60"
        )
        sys.exit(1)
    # Use the globally decorated bot instance with guarded login to avoid silent hangs
    try:
        bot.run(token)
    except discord.errors.LoginFailure as e:
        log_event("login_failed", level="ERROR", error=str(e))
        print(f"❌ Login failed: {e}. Check DISCORD_BOT_TOKEN or regenerate the token.")
        sys.exit(1)
    except Exception as e:
        log_event("login_error", level="ERROR", error=str(e))
        print(f"❌ Unexpected error during login: {e}")
        sys.exit(1)


# --- CLI fallback for quick testing ---
if __name__ == "__main__":
    if len(sys.argv) == 6:
        try:
            O, C, E, A, N = map(float, sys.argv[1:])
            role, desc, dept, score = match_role(O, C, E, A, N)
            print(f"Role: {role}\nDept: {dept}\nDesc: {desc}\nScore: {score:.3f}")
        except Exception as e:
            print("Error:", e)
            print("Usage: python main.py O C E A N")
            sys.exit(1)
    else:
        # Run discord bot if no CLI args
        run_discord()