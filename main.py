import os
import sys
import yaml
import discord
from dotenv import load_dotenv
from collections import Counter

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
    except discord.HTTPException:
        # Simple backoff: inform user
        try:
            msg = "⚠️ Rate limited, please try again."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass


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
    guild = interaction.guild
    guild_id = guild.id if guild else None
    if guild_id is None:
        await send_safe(interaction, "🏢 This command can only be used in a server.", ephemeral=True)
        return
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


@bot.tree.command(name="departments", description="List company members by department")
async def departments_command(interaction: discord.Interaction):
    guild = interaction.guild
    guild_id = guild.id if guild else None
    if guild_id is None:
        await send_safe(interaction, "🏢 This command can only be used in a server.", ephemeral=True)
        return

    registry = companies.get(guild_id, {})
    if not registry:
        await send_safe(interaction, "🏢 No members registered yet in this company.", ephemeral=True)
        return

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
@discord.app_commands.describe(detailed="Show detailed OCEAN averages with bars")
async def summary_command(interaction: discord.Interaction, detailed: bool = False):
    guild = interaction.guild
    guild_id = guild.id if guild else None
    if guild_id is None:
        await send_safe(interaction, "🏢 This command can only be used in a server.", ephemeral=True)
        return

    registry = companies.get(guild_id, {})
    if not registry:
        await send_safe(interaction, "🏢 No members registered yet in this company.", ephemeral=True)
        return

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

    if detailed:
        bars = "\n".join([
            f"{t}: {make_bar(norm[t])} ({norm[t]:+.2f})"
            for t in ["O", "C", "E", "A", "N"]
        ])
        bars_section = f"\n\n**Average OCEAN Profile:**\n{bars}"
    else:
        bars_section = ""

    # Optional compact text summary (goes below the bars)
    if detailed:
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

        balance_line = (
            f"\n🧭 *Team OCEAN balance: {label_trait(dominant)} dominant, "
            f"{label_trait(weakest)} low.*"
        )
    else:
        balance_line = ""

    if detailed:
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


@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    lines = [
        "Commands:",
        "/ocean o c e a n — five numbers (0–120) to get your archetype and department.",
        "/profile — view your current archetype and OCEAN scores.",
        "/company — list members registered in this server (company).",
        "/departments — list members grouped by department.",
        "/summary — view company-wide department and role summary.",
        "/forget — delete your stored data from this server.",
    ]
    await send_safe(interaction, "\n".join(lines), ephemeral=True)


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


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    # Basic global error handler for application commands
    try:
        msg = "⚠️ Something went wrong. Please try again."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass
    # Log to console for operator visibility
    print(f"App command error: {error}")


def run_discord():
    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("YOUR_DISCORD_BOT_TOKEN")
    if not token:
        print(
            "❌ Missing DISCORD_BOT_TOKEN. Set it in your environment or in a .env file.\n"
            "Example .env line:\nDISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN\n\n"
            "Tip: For a quick local test without Discord, run: python main.py 105 90 95 83 60"
        )
        sys.exit(1)
    # Use the globally decorated bot instance
    bot.run(token)


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