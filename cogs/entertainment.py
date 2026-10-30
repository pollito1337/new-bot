import random

import discord
from discord import app_commands
from discord.ext import commands

NO_MENTIONS = discord.AllowedMentions.none()

FORTUNES = [
    "A surprise is waiting for you where you least expect it.",
    "Someone is about to ask for your advice. Give it honestly.",
    "The project you're avoiding is smaller than it looks.",
    "You'll finish the thing you started last week.",
    "Take a walk. The answer will show up on the way back.",
    "A good conversation is coming your way today.",
    "Don't trust a deal that expires in five minutes.",
    "The snack you're thinking about is worth it.",
]

COMPLIMENTS = [
    "has excellent taste in memes",
    "makes this server a better place",
    "could make a whole room laugh",
    "always shows up when it matters",
    "would win a staring contest against a cat",
]


class Entertainment(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="fortune", description="Get a fortune")
    async def fortune_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🥠 {random.choice(FORTUNES)}")

    @app_commands.command(name="compliment", description="Compliment someone")
    @app_commands.guild_only()
    @app_commands.describe(member="Who to compliment")
    async def compliment_cmd(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{member.display_name} {random.choice(COMPLIMENTS)}.", allowed_mentions=NO_MENTIONS
        )

    @app_commands.command(name="clap", description="Put 👏 between every word")
    @app_commands.describe(text="The text")
    async def clap_cmd(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, 300]):
        words = text.split()
        if not words:
            return await interaction.response.send_message("send some words.", ephemeral=True)
        await interaction.response.send_message(" 👏 ".join(words), allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="randnum", description="Random whole number between two values")
    @app_commands.describe(minimum="Lowest possible value", maximum="Highest possible value")
    async def randnum_cmd(
        self,
        interaction: discord.Interaction,
        minimum: app_commands.Range[int, -1000000, 1000000],
        maximum: app_commands.Range[int, -1000000, 1000000],
    ):
        low, high = sorted((minimum, maximum))
        await interaction.response.send_message(f"🎲 **{random.randint(low, high)}** (between {low} and {high})")


async def setup(bot: commands.Bot):
    await bot.add_cog(Entertainment(bot))
