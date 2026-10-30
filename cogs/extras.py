import base64
import binascii
import hashlib
import random

import discord
from discord import app_commands
from discord.ext import commands

NO_MENTIONS = discord.AllowedMentions.none()

JOKES = [
    "I'm reading a book about anti-gravity. It's impossible to put down.",
    "Why don't skeletons fight each other? They don't have the guts.",
    "What do you call fake spaghetti? An impasta.",
    "Why did the scarecrow win an award? He was outstanding in his field.",
    "I used to hate facial hair, but then it grew on me.",
    "What do you call a bear with no teeth? A gummy bear.",
    "Why can't you give Elsa a balloon? Because she will let it go.",
    "I'd tell you a UDP joke, but you might not get it.",
]


def to_emoji_text(text: str) -> str:
    """Turn letters and digits into emoji. Spaces become a visible separator."""
    tokens = []
    for ch in text.lower():
        if "a" <= ch <= "z":
            tokens.append(chr(0x1F1E6 + ord(ch) - ord("a")))  # regional indicator letters
        elif ch in "0123456789":
            tokens.append(f"{ch}\u20e3")
        elif ch == " ":
            tokens.append("\u2b1c")
    return " ".join(tokens)


def ship_score(a: int, b: int) -> int:
    """Same two IDs always give the same score, in either order."""
    lo, hi = sorted((a, b))
    digest = hashlib.sha256(f"{lo}-{hi}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 101


class Extras(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.started = discord.utils.utcnow()

    @app_commands.command(name="uptime", description="How long the bot has been running")
    async def uptime(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"i've been up since {discord.utils.format_dt(self.started, 'R')}.")

    @app_commands.command(name="reverse", description="Reverse some text")
    @app_commands.describe(text="What to reverse")
    async def reverse(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, 300]):
        await interaction.response.send_message(text[::-1], allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="emojify", description="Turn text into emoji letters")
    @app_commands.describe(text="Letters and numbers, up to 40 characters")
    async def emojify(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, 40]):
        result = to_emoji_text(text)
        if not result:
            return await interaction.response.send_message("i need some letters or numbers in there.", ephemeral=True)
        await interaction.response.send_message(result, allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="base64", description="Encode or decode base64 text")
    @app_commands.describe(mode="encode or decode", text="The text to convert")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="encode", value="encode"),
            app_commands.Choice(name="decode", value="decode"),
        ]
    )
    async def base64_cmd(self, interaction: discord.Interaction, mode: str, text: app_commands.Range[str, 1, 800]):
        if mode == "encode":
            result = base64.b64encode(text.encode("utf-8")).decode("ascii")
        else:
            try:
                result = base64.b64decode(text, validate=True).decode("utf-8")
            except ValueError:  # covers binascii.Error and UnicodeDecodeError
                return await interaction.response.send_message("that's not valid base64.", ephemeral=True)
        await interaction.response.send_message(f"```\n{result}\n```", allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="ship", description="Compatibility score between two people")
    @app_commands.guild_only()
    @app_commands.describe(first="Someone", second="Someone else")
    async def ship(self, interaction: discord.Interaction, first: discord.Member, second: discord.Member):
        score = ship_score(first.id, second.id)
        filled = score // 10
        bar = "█" * filled + "░" * (10 - filled)
        embed = discord.Embed(
            title="💘 Ship meter",
            description=f"{first.display_name} + {second.display_name}\n`{bar}` **{score}%**",
            color=discord.Color.pink(),
        )
        await interaction.response.send_message(embed=embed, allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="hug", description="Hug someone")
    @app_commands.guild_only()
    @app_commands.describe(member="Who to hug")
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} hugs {member.mention} 🤗", allowed_mentions=NO_MENTIONS
        )

    @app_commands.command(name="joke", description="Get a dad joke")
    async def joke(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(JOKES))

    @app_commands.command(name="rate", description="I'll rate something out of 10")
    @app_commands.describe(thing="What to rate")
    async def rate(self, interaction: discord.Interaction, thing: app_commands.Range[str, 1, 100]):
        score = random.randint(0, 10)
        await interaction.response.send_message(f"i rate **{thing}** {score}/10.", allowed_mentions=NO_MENTIONS)


async def setup(bot: commands.Bot):
    await bot.add_cog(Extras(bot))
