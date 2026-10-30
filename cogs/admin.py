import discord
from discord import app_commands
from discord.ext import commands

NO_MENTIONS = discord.AllowedMentions.none()


def role_problem(interaction: discord.Interaction, role: discord.Role) -> str | None:
    guild = interaction.guild
    if role.is_default():
        return "that's the @everyone role, it can't be changed."
    if role.managed:
        return "that role is managed by an integration."
    if role >= guild.me.top_role:
        return "that role is equal to or above my top role, so i can't manage it."
    if interaction.user.id != guild.owner_id and role >= interaction.user.top_role:
        return "that role is equal to or above your top role."
    return None


class Admin(commands.Cog):
    role = app_commands.Group(name="role", description="Give or take roles")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="purge", description="Delete recent messages from one member in this channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    @app_commands.describe(member="Whose messages to delete", amount="How many recent messages to scan (1 to 100)")
    async def purge_cmd(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[int, 1, 100],
    ):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount, check=lambda m: m.author.id == member.id)
        await interaction.followup.send(
            f"deleted {len(deleted)} messages from {member.display_name}.", ephemeral=True
        )

    @app_commands.command(name="announce", description="Post an announcement embed in a channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(title="Headline", message="The announcement", channel="Where to post it")
    async def announce_cmd(
        self,
        interaction: discord.Interaction,
        title: app_commands.Range[str, 1, 256],
        message: app_commands.Range[str, 1, 4000],
        channel: discord.TextChannel,
    ):
        embed = discord.Embed(title=title, description=message, color=discord.Color.blurple())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        try:
            await channel.send(embed=embed, allowed_mentions=NO_MENTIONS)
        except discord.Forbidden:
            return await interaction.response.send_message("i can't post in that channel.", ephemeral=True)
        await interaction.response.send_message(f"posted in {channel.mention}.", ephemeral=True)

    @role.command(name="give", description="Give a role to a member")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    @app_commands.describe(member="Who gets the role", role="The role to give")
    async def role_give(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if problem := role_problem(interaction, role):
            return await interaction.response.send_message(problem, ephemeral=True)
        if role in member.roles:
            return await interaction.response.send_message(
                f"{member.display_name} already has that role.", ephemeral=True
            )
        try:
            await member.add_roles(role, reason=f"{interaction.user}: /role give")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "i don't have permission to do that for this member.", ephemeral=True
            )
        await interaction.response.send_message(
            f"gave **{role.name}** to {member.display_name}.", allowed_mentions=NO_MENTIONS
        )

    @role.command(name="take", description="Remove a role from a member")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    @app_commands.describe(member="Who loses the role", role="The role to remove")
    async def role_take(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if problem := role_problem(interaction, role):
            return await interaction.response.send_message(problem, ephemeral=True)
        if role not in member.roles:
            return await interaction.response.send_message(
                f"{member.display_name} doesn't have that role.", ephemeral=True
            )
        try:
            await member.remove_roles(role, reason=f"{interaction.user}: /role take")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "i don't have permission to do that for this member.", ephemeral=True
            )
        await interaction.response.send_message(
            f"removed **{role.name}** from {member.display_name}.", allowed_mentions=NO_MENTIONS
        )

    @app_commands.command(name="invite", description="Create an invite link for this channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(create_instant_invite=True)
    @app_commands.checks.has_permissions(create_instant_invite=True)
    @app_commands.checks.bot_has_permissions(create_instant_invite=True)
    @app_commands.describe(hours="How long the link lasts, 0 for never (max 168)")
    async def invite_cmd(self, interaction: discord.Interaction, hours: app_commands.Range[int, 0, 168] = 24):
        channel = interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
            return await interaction.response.send_message(
                "i can't make invites for this kind of channel.", ephemeral=True
            )
        link = await channel.create_invite(max_age=hours * 3600, reason=f"{interaction.user}: /invite")
        expiry = "never" if hours == 0 else f"in {hours} hours"
        await interaction.response.send_message(f"invite (expires {expiry}): {link.url}", ephemeral=True)

    @app_commands.command(name="emojis", description="Show this server's custom emojis")
    @app_commands.guild_only()
    async def emojis_cmd(self, interaction: discord.Interaction):
        all_emojis = interaction.guild.emojis
        if not all_emojis:
            return await interaction.response.send_message("this server has no custom emojis.", ephemeral=True)
        shown = " ".join(str(e) for e in all_emojis[:60])
        embed = discord.Embed(title=f"Emojis ({len(all_emojis)})", description=shown, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
