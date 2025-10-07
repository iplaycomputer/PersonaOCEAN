import os
import sys
import yaml
import discord
from dotenv import load_dotenv

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
async def send_safe(interaction: discord.Interaction, content: str, *, ephemeral: bool = False):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(content, ephemeral=ephemeral)
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
        display = member.display_name if member else f"User {uid}"
        lines.append(f"- {display}: {data['role']} ({data['dept']})")
    await send_safe(interaction, f"🏢 **{guild.name} Company Members:**\n" + "\n".join(lines), ephemeral=False)


@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    lines = [
        "Commands:",
        "/ocean O C E A N — five numbers (0–120) to get your archetype and department.",
        "/company — list members registered in this server (company).",
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
