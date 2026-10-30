import datetime
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = sqlite3.connect("bot.db")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS warns ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER, "
            "mod_id INTEGER, reason TEXT, ts TEXT)"
        )
        self.db.commit()

    async def cog_unload(self):
        self.db.close()

    @staticmethod
    def _hierarchy_ok(interaction: discord.Interaction, target: discord.Member) -> str | None:
        """Return an error string if the action shouldn't be allowed, else None."""
        guild = interaction.guild
        if target.id == interaction.user.id:
            return "you can't do that to yourself."
        if target.id == guild.owner_id:
            return "you can't touch the server owner."
        if interaction.user.id != guild.owner_id and target.top_role >= interaction.user.top_role:
            return "that member's role is equal to or above yours."
        if target.top_role >= guild.me.top_role:
            return "that member's role is equal to or above mine."
        return None

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if err := self._hierarchy_ok(interaction, member):
            return await interaction.response.send_message(err, ephemeral=True)
        await member.kick(reason=f"{interaction.user}: {reason}")
        await interaction.response.send_message(f"kicked **{member}**. reason: {reason}")

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if err := self._hierarchy_ok(interaction, member):
            return await interaction.response.send_message(err, ephemeral=True)
        await member.ban(reason=f"{interaction.user}: {reason}", delete_message_days=0)
        await interaction.response.send_message(f"banned **{member}**. reason: {reason}")

    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
        except (ValueError, discord.NotFound):
            return await interaction.response.send_message("couldn't find that ban.", ephemeral=True)
        await interaction.response.send_message(f"unbanned **{user}**.")

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(minutes="Duration in minutes (max 40320 = 28 days)")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "No reason provided",
    ):
        if err := self._hierarchy_ok(interaction, member):
            return await interaction.response.send_message(err, ephemeral=True)
        await member.timeout(datetime.timedelta(minutes=minutes), reason=f"{interaction.user}: {reason}")
        await interaction.response.send_message(f"timed out **{member}** for {minutes} min. reason: {reason}")

    @app_commands.command(name="untimeout", description="Remove a member's timeout")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        await interaction.response.send_message(f"removed timeout from **{member}**.")

    @app_commands.command(name="clear", description="Bulk delete recent messages")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"deleted {len(deleted)} messages.", ephemeral=True)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if err := self._hierarchy_ok(interaction, member):
            return await interaction.response.send_message(err, ephemeral=True)
        self.db.execute(
            "INSERT INTO warns (guild_id, user_id, mod_id, reason, ts) VALUES (?,?,?,?,?)",
            (interaction.guild_id, member.id, interaction.user.id, reason,
             datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )
        self.db.commit()
        count = self.db.execute(
            "SELECT COUNT(*) FROM warns WHERE guild_id=? AND user_id=?", (interaction.guild_id, member.id)
        ).fetchone()[0]
        await interaction.response.send_message(f"warned **{member}** ({count} total). reason: {reason}")

    @app_commands.command(name="warnings", description="List a member's warnings")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        rows = self.db.execute(
            "SELECT id, reason, ts FROM warns WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 15",
            (interaction.guild_id, member.id),
        ).fetchall()
        if not rows:
            return await interaction.response.send_message(f"{member} has no warnings.", ephemeral=True)
        lines = [f"`#{i}` {r} ({ts[:10]})" for i, r, ts in rows]
        embed = discord.Embed(title=f"Warnings for {member}", description="\n".join(lines), color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarns", description="Clear all warnings for a member")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        self.db.execute("DELETE FROM warns WHERE guild_id=? AND user_id=?", (interaction.guild_id, member.id))
        self.db.commit()
        await interaction.response.send_message(f"cleared warnings for **{member}**.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
