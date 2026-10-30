import logging
import os

import discord
from discord.ext import commands

log = logging.getLogger("welcome")


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = int(os.getenv("WELCOME_CHANNEL_ID") or 0)
        self.role_id = int(os.getenv("AUTO_ROLE_ID") or 0)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if self.role_id:
            role = member.guild.get_role(self.role_id)
            if role:
                try:
                    await member.add_roles(role, reason="auto role")
                except discord.Forbidden:
                    log.warning("can't assign auto role; move my role above it")

        if self.channel_id:
            channel = member.guild.get_channel(self.channel_id)
            if channel:
                embed = discord.Embed(
                    title="Welcome!",
                    description=f"{member.mention} just joined **{member.guild.name}**. "
                                f"You're member #{member.guild.member_count}.",
                    color=discord.Color.green(),
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
