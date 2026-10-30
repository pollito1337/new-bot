import platform

import discord
from discord import app_commands
from discord.ext import commands

NO_MENTIONS = discord.AllowedMentions.none()


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.started = discord.utils.utcnow()

    @app_commands.command(name="botinfo", description="Stats about this bot")
    async def botinfo_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Bot info", color=discord.Color.blurple())
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(name="Users (cached)", value=str(len(self.bot.users)))
        embed.add_field(name="Commands", value=str(len(self.bot.tree.get_commands())))
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)} ms")
        embed.add_field(name="discord.py", value=discord.__version__)
        embed.add_field(name="Python", value=platform.python_version())
        embed.add_field(name="Online since", value=discord.utils.format_dt(self.started, "R"), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="snowflake", description="Find when a Discord ID was created")
    @app_commands.describe(snowflake_id="A user, channel, server or message ID")
    async def snowflake_cmd(self, interaction: discord.Interaction, snowflake_id: app_commands.Range[str, 1, 25]):
        if not snowflake_id.isdigit():
            return await interaction.response.send_message(
                "that doesn't look like an ID. turn on Developer Mode, then right-click something and choose Copy ID.",
                ephemeral=True,
            )
        created = discord.utils.snowflake_time(int(snowflake_id))
        await interaction.response.send_message(
            f"`{snowflake_id}` was created {discord.utils.format_dt(created, 'F')} "
            f"({discord.utils.format_dt(created, 'R')})."
        )

    @app_commands.command(name="roles", description="List this server's roles")
    @app_commands.guild_only()
    async def roles_cmd(self, interaction: discord.Interaction):
        roles = [r for r in reversed(interaction.guild.roles) if not r.is_default()]
        if not roles:
            return await interaction.response.send_message("this server has no roles besides @everyone.", ephemeral=True)
        shown = " ".join(r.mention for r in roles[:40])
        embed = discord.Embed(title=f"Roles ({len(roles)})", description=shown, color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, allowed_mentions=NO_MENTIONS)


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
