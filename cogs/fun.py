import random

import discord
from discord import app_commands
from discord.ext import commands

EIGHT_BALL = [
    "yeah, obviously.", "without a doubt.", "signs point to yes.", "probably.",
    "ask me later.", "can't tell you right now.", "don't count on it.",
    "my sources say no.", "very doubtful.", "absolutely not.",
]


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="8ball", description="Ask the magic 8-ball")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        await interaction.response.send_message(f"**{question}**\n{random.choice(EIGHT_BALL)}")

    @app_commands.command(name="roll", description="Roll dice, e.g. 2d6")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d6"):
        try:
            n, sides = dice.lower().split("d")
            n, sides = int(n or 1), int(sides)
            assert 1 <= n <= 100 and 2 <= sides <= 1000
        except Exception:
            return await interaction.response.send_message("format is NdM, like 2d6 (max 100d1000).", ephemeral=True)
        rolls = [random.randint(1, sides) for _ in range(n)]
        shown = ", ".join(map(str, rolls)) if n <= 20 else f"{n} dice"
        await interaction.response.send_message(f"{dice}: [{shown}] = **{sum(rolls)}**")

    @app_commands.command(name="coinflip", description="Flip a coin")
    async def coinflip(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(["heads", "tails"]))

    @app_commands.command(name="choose", description="Pick one option for you")
    @app_commands.describe(options="Separate with commas")
    async def choose(self, interaction: discord.Interaction, options: str):
        items = [o.strip() for o in options.split(",") if o.strip()]
        if len(items) < 2:
            return await interaction.response.send_message("give me at least 2 options, comma separated.", ephemeral=True)
        await interaction.response.send_message(f"i pick **{random.choice(items)}**")


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
