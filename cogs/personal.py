import datetime
import sqlite3
import zoneinfo

import discord
from discord import app_commands
from discord.ext import commands


class Personal(commands.Cog):
    todo = app_commands.Group(name="todo", description="Your personal to-do list (only you can see it)")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = sqlite3.connect("bot.db")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS todos ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
            "text TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL)"
        )
        self.db.commit()

    async def cog_unload(self):
        self.db.close()

    @todo.command(name="add", description="Add a task")
    @app_commands.describe(text="What to do")
    async def todo_add(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, 200]):
        cur = self.db.execute(
            "INSERT INTO todos (user_id, text, created) VALUES (?, ?, ?)",
            (interaction.user.id, text, datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )
        self.db.commit()
        await interaction.response.send_message(f"added task `#{cur.lastrowid}`.", ephemeral=True)

    @todo.command(name="list", description="Show your tasks")
    async def todo_list(self, interaction: discord.Interaction):
        rows = self.db.execute(
            "SELECT id, text, done FROM todos WHERE user_id=? ORDER BY done, id LIMIT 25",
            (interaction.user.id,),
        ).fetchall()
        if not rows:
            return await interaction.response.send_message(
                "your list is empty. use `/todo add` to start.", ephemeral=True
            )
        lines = [f"{'✅' if done else '⬜'} `#{tid}` {text}" for tid, text, done in rows]
        embed = discord.Embed(title="Your to-do list", description="\n".join(lines), color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @todo.command(name="done", description="Mark a task as done")
    @app_commands.describe(task_id="The number shown in /todo list")
    async def todo_done(self, interaction: discord.Interaction, task_id: int):
        cur = self.db.execute(
            "UPDATE todos SET done=1 WHERE id=? AND user_id=?", (task_id, interaction.user.id)
        )
        self.db.commit()
        msg = "marked as done." if cur.rowcount else "no task with that number."
        await interaction.response.send_message(msg, ephemeral=True)

    @todo.command(name="remove", description="Delete a task")
    @app_commands.describe(task_id="The number shown in /todo list")
    async def todo_remove(self, interaction: discord.Interaction, task_id: int):
        cur = self.db.execute("DELETE FROM todos WHERE id=? AND user_id=?", (task_id, interaction.user.id))
        self.db.commit()
        msg = "task deleted." if cur.rowcount else "no task with that number."
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="time", description="Current time in a time zone")
    @app_commands.describe(zone="For example Europe/Madrid or America/New_York")
    async def time_cmd(self, interaction: discord.Interaction, zone: app_commands.Range[str, 1, 50]):
        try:
            tz = zoneinfo.ZoneInfo(zone)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            return await interaction.response.send_message(
                "unknown time zone. use a name like `Europe/Madrid` or `America/New_York`.", ephemeral=True
            )
        now = datetime.datetime.now(tz)
        await interaction.response.send_message(
            f"**{zone}**: {now:%A %d %B %Y, %H:%M} ({discord.utils.format_dt(now, 'T')} in your time)"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Personal(bot))
