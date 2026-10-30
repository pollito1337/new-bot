import logging
import math
import random
import sqlite3
import time

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("levels")

NO_MENTIONS = discord.AllowedMentions.none()
XP_MIN, XP_MAX = 15, 25
COOLDOWN = 60  # seconds between XP gains for the same member


def level_for(xp: int) -> int:
    return int(math.sqrt(xp / 100))


def xp_for_level(level: int) -> int:
    return 100 * level * level


class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = sqlite3.connect("bot.db")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS levels ("
            "guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
            "xp INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, user_id))"
        )
        self.db.commit()
        self._last_gain: dict[tuple[int, int], float] = {}

    async def cog_unload(self):
        self.db.close()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        if now - self._last_gain.get(key, -COOLDOWN) < COOLDOWN:
            return
        self._last_gain[key] = now

        row = self.db.execute("SELECT xp FROM levels WHERE guild_id=? AND user_id=?", key).fetchone()
        before = row[0] if row else 0
        after = before + random.randint(XP_MIN, XP_MAX)
        self.db.execute(
            "INSERT INTO levels (guild_id, user_id, xp) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = excluded.xp",
            (key[0], key[1], after),
        )
        self.db.commit()

        if level_for(after) > level_for(before):
            try:
                await message.channel.send(
                    f"{message.author.mention} reached **level {level_for(after)}**!",
                    allowed_mentions=discord.AllowedMentions(
                        everyone=False, roles=False, users=[message.author]
                    ),
                )
            except discord.HTTPException:
                log.warning("couldn't post level-up message")

    @app_commands.command(name="rank", description="Show your level, or someone else's")
    @app_commands.guild_only()
    @app_commands.describe(member="Whose rank to show (default: you)")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        row = self.db.execute(
            "SELECT xp FROM levels WHERE guild_id=? AND user_id=?", (interaction.guild_id, member.id)
        ).fetchone()
        xp = row[0] if row else 0
        level = level_for(xp)
        floor_xp, next_xp = xp_for_level(level), xp_for_level(level + 1)
        filled = int((xp - floor_xp) / (next_xp - floor_xp) * 10)
        bar = "█" * filled + "░" * (10 - filled)
        position = self.db.execute(
            "SELECT COUNT(*) + 1 FROM levels WHERE guild_id=? AND xp > ?", (interaction.guild_id, xp)
        ).fetchone()[0]

        embed = discord.Embed(
            title=member.display_name,
            description=f"Level **{level}** · rank **#{position}**\n`{bar}` {xp}/{next_xp} XP",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="The 10 most active members")
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        rows = self.db.execute(
            "SELECT user_id, xp FROM levels WHERE guild_id=? ORDER BY xp DESC LIMIT 10",
            (interaction.guild_id,),
        ).fetchall()
        if not rows:
            return await interaction.response.send_message(
                "nobody has earned xp yet. go say something!", ephemeral=True
            )
        lines = [f"`{i}.` <@{uid}> · level {level_for(xp)} ({xp} XP)" for i, (uid, xp) in enumerate(rows, 1)]
        embed = discord.Embed(title="🏆 Leaderboard", description="\n".join(lines), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, allowed_mentions=NO_MENTIONS)


async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))
