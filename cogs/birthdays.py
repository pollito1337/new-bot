import datetime
import re
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

NO_MENTIONS = discord.AllowedMentions.none()
DATE_RE = re.compile(r"^(\d{1,2})[-/](\d{1,2})$")


def parse_month_day(text: str):
    """Returns (month, day) for input like 03-14 or 3/14, or None if it isn't a real date."""
    match = DATE_RE.match(text.strip())
    if not match:
        return None
    month, day = int(match.group(1)), int(match.group(2))
    try:
        datetime.date(2000, month, day)  # 2000 is a leap year, so Feb 29 is allowed
    except ValueError:
        return None
    return month, day


def next_birthday(month: int, day: int, today: datetime.date) -> datetime.date:
    """The next occurrence of a birthday, counting today. Feb 29 is celebrated on Feb 28 in other years."""
    for year in (today.year, today.year + 1):
        try:
            candidate = datetime.date(year, month, day)
        except ValueError:
            candidate = datetime.date(year, 2, 28)
        if candidate >= today:
            return candidate
    raise RuntimeError("unreachable")


def days_text(days: int) -> str:
    if days == 0:
        return "today"
    return f"in {days} day{'s' if days != 1 else ''}"


class Birthdays(commands.Cog):
    birthday = app_commands.Group(name="birthday", description="Save and look up birthdays")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = sqlite3.connect("bot.db")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS birthdays ("
            "guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
            "month INTEGER NOT NULL, day INTEGER NOT NULL, PRIMARY KEY (guild_id, user_id))"
        )
        self.db.commit()

    async def cog_unload(self):
        self.db.close()

    @birthday.command(name="set", description="Save your birthday")
    @app_commands.guild_only()
    @app_commands.describe(when="Month and day, like 03-14")
    async def birthday_set(self, interaction: discord.Interaction, when: app_commands.Range[str, 1, 10]):
        parsed = parse_month_day(when)
        if parsed is None:
            return await interaction.response.send_message(
                "use the format `MM-DD`, for example `03-14`.", ephemeral=True
            )
        month, day = parsed
        self.db.execute(
            "INSERT INTO birthdays (guild_id, user_id, month, day) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET month = excluded.month, day = excluded.day",
            (interaction.guild_id, interaction.user.id, month, day),
        )
        self.db.commit()
        await interaction.response.send_message(
            f"saved your birthday as {datetime.date(2000, month, day):%B %d}.", ephemeral=True
        )

    @birthday.command(name="show", description="Show someone's birthday")
    @app_commands.guild_only()
    @app_commands.describe(member="Whose birthday (default: yours)")
    async def birthday_show(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        row = self.db.execute(
            "SELECT month, day FROM birthdays WHERE guild_id=? AND user_id=?",
            (interaction.guild_id, member.id),
        ).fetchone()
        if not row:
            return await interaction.response.send_message(
                f"{member.display_name} hasn't saved a birthday yet.", ephemeral=True
            )
        month, day = row
        await interaction.response.send_message(
            f"{member.display_name}'s birthday is {datetime.date(2000, month, day):%B %d}.",
            allowed_mentions=NO_MENTIONS,
        )

    @birthday.command(name="remove", description="Delete your saved birthday")
    @app_commands.guild_only()
    async def birthday_remove(self, interaction: discord.Interaction):
        cur = self.db.execute(
            "DELETE FROM birthdays WHERE guild_id=? AND user_id=?", (interaction.guild_id, interaction.user.id)
        )
        self.db.commit()
        msg = "removed your birthday." if cur.rowcount else "you don't have a birthday saved."
        await interaction.response.send_message(msg, ephemeral=True)

    @birthday.command(name="list", description="The next 10 birthdays in this server")
    @app_commands.guild_only()
    async def birthday_list(self, interaction: discord.Interaction):
        rows = self.db.execute(
            "SELECT user_id, month, day FROM birthdays WHERE guild_id=?", (interaction.guild_id,)
        ).fetchall()
        if not rows:
            return await interaction.response.send_message(
                "no birthdays saved yet. use `/birthday set`.", ephemeral=True
            )
        today = datetime.datetime.now(datetime.timezone.utc).date()
        upcoming = sorted((next_birthday(m, d, today), uid) for uid, m, d in rows)[:10]
        lines = [
            f"<@{uid}> · {when:%B %d} ({days_text((when - today).days)})" for when, uid in upcoming
        ]
        embed = discord.Embed(title="🎂 Upcoming birthdays", description="\n".join(lines), color=discord.Color.magenta())
        await interaction.response.send_message(embed=embed, allowed_mentions=NO_MENTIONS)


async def setup(bot: commands.Bot):
    await bot.add_cog(Birthdays(bot))
