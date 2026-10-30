import os
import random

import discord
from discord import app_commands
from discord.ext import commands

NO_MENTIONS = discord.AllowedMentions.none()

LENGTH_M = {"m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
MASS_KG = {"kg": 1.0, "g": 0.001, "oz": 0.028349523125, "lb": 0.45359237}
TEMP_UNITS = ("c", "f", "k")

WOULD_YOU_RATHER = [
    ("be able to fly", "be invisible"),
    ("always be 10 minutes late", "always be 20 minutes early"),
    ("have a rewind button", "have a pause button"),
    ("read minds", "see the future"),
    ("eat only pizza forever", "never eat pizza again"),
    ("live without music", "live without movies"),
    ("explore the ocean", "explore space"),
    ("speak every language", "talk to animals"),
    ("have unlimited coffee", "have unlimited tacos"),
    ("be famous for something silly", "be a secret genius nobody knows about"),
]


def convert_units(value: float, src: str, dst: str) -> float:
    src, dst = src.lower(), dst.lower()
    if src in TEMP_UNITS and dst in TEMP_UNITS:
        if src == "c":
            celsius = value
        elif src == "f":
            celsius = (value - 32) * 5 / 9
        else:
            celsius = value - 273.15
        if celsius < -273.15:
            raise ValueError("that's below absolute zero")
        if dst == "c":
            return celsius
        if dst == "f":
            return celsius * 9 / 5 + 32
        return celsius + 273.15
    for table in (LENGTH_M, MASS_KG):
        if src in table and dst in table:
            return value * table[src] / table[dst]
    raise ValueError("can't convert between those units")


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.suggestions_channel_id = int(os.getenv("SUGGESTIONS_CHANNEL_ID") or 0)

    @app_commands.command(name="convert", description="Convert length, weight or temperature")
    @app_commands.describe(
        value="The number to convert",
        from_unit="e.g. km, mi, kg, lb, c, f",
        to_unit="e.g. mi, km, lb, kg, f, c",
    )
    async def convert_cmd(
        self,
        interaction: discord.Interaction,
        value: float,
        from_unit: app_commands.Range[str, 1, 5],
        to_unit: app_commands.Range[str, 1, 5],
    ):
        try:
            result = convert_units(value, from_unit, to_unit)
        except ValueError as e:
            return await interaction.response.send_message(
                f"{e}. units: m, km, cm, mm, in, ft, yd, mi, kg, g, lb, oz, c, f, k.", ephemeral=True
            )
        await interaction.response.send_message(f"{value:g} {from_unit.lower()} = **{result:.6g} {to_unit.lower()}**")

    @app_commands.command(name="wyr", description="Would you rather...")
    async def wyr(self, interaction: discord.Interaction):
        a, b = random.choice(WOULD_YOU_RATHER)
        embed = discord.Embed(
            title="Would you rather...",
            description=f"1\u20e3 {a}\n\n**or**\n\n2\u20e3 {b}",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("1\u20e3")
        await msg.add_reaction("2\u20e3")

    @app_commands.command(name="suggest", description="Send an idea to the server team")
    @app_commands.guild_only()
    @app_commands.describe(idea="Your suggestion")
    async def suggest(self, interaction: discord.Interaction, idea: app_commands.Range[str, 1, 1000]):
        if not self.suggestions_channel_id:
            return await interaction.response.send_message(
                "suggestions aren't set up yet. an admin needs to set SUGGESTIONS_CHANNEL_ID.", ephemeral=True
            )
        channel = self.bot.get_channel(self.suggestions_channel_id)
        if channel is None:
            return await interaction.response.send_message(
                "i can't find the suggestions channel. check SUGGESTIONS_CHANNEL_ID.", ephemeral=True
            )
        embed = discord.Embed(title="💡 Suggestion", description=idea, color=discord.Color.gold())
        embed.set_footer(text=f"from {interaction.user.display_name}")
        try:
            msg = await channel.send(embed=embed, allowed_mentions=NO_MENTIONS)
            await msg.add_reaction("\u2705")
            await msg.add_reaction("\u274c")
        except discord.HTTPException:
            return await interaction.response.send_message(
                "i couldn't post in that channel. check my permissions there.", ephemeral=True
            )
        await interaction.response.send_message(f"posted in {channel.mention}. thanks!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Misc(bot))
