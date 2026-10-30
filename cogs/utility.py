import discord
from discord import app_commands
from discord.ext import commands


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="List all commands")
    async def help(self, interaction: discord.Interaction):
        pages = []
        page = discord.Embed(title="Commands", color=discord.Color.blurple())
        used = 0
        for cog_name, cog in self.bot.cogs.items():
            cmds = cog.get_app_commands()
            if not cmds:
                continue
            lines = [f"`/{c.name}` - {c.description}" for c in cmds]
            parts, chunk, size = [], [], 0
            for line in lines:
                if chunk and size + len(line) > 900:
                    parts.append(chunk)
                    chunk, size = [], 0
                chunk.append(line)
                size += len(line) + 1
            if chunk:
                parts.append(chunk)
            for i, part in enumerate(parts, 1):
                name = cog_name if len(parts) == 1 else f"{cog_name} ({i}/{len(parts)})"
                value = "\n".join(part)
                if len(page.fields) >= 20 or used + len(name) + len(value) > 5000:
                    pages.append(page)
                    page = discord.Embed(title="Commands (cont.)", color=discord.Color.blurple())
                    used = 0
                page.add_field(name=name, value=value, inline=False)
                used += len(name) + len(value)
        pages.append(page)
        await interaction.response.send_message(embeds=pages[:10], ephemeral=True)

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"pong. {round(self.bot.latency * 1000)}ms")

    @app_commands.command(name="avatar", description="Show a user's avatar")
    async def avatar(self, interaction: discord.Interaction, user: discord.User | None = None):
        user = user or interaction.user
        embed = discord.Embed(title=f"{user.display_name}'s avatar", color=discord.Color.blurple())
        embed.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Info about a member")
    @app_commands.guild_only()
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        embed = discord.Embed(title=str(member), color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Created", value=discord.utils.format_dt(member.created_at, "R"))
        embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, "R") if member.joined_at else "?")
        roles = [r.mention for r in reversed(member.roles) if r != interaction.guild.default_role]
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles[:15]) or "none", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Info about this server")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        embed = discord.Embed(title=g.name, color=discord.Color.blurple())
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=g.owner.mention if g.owner else "?")
        embed.add_field(name="Members", value=g.member_count)
        embed.add_field(name="Channels", value=len(g.channels))
        embed.add_field(name="Roles", value=len(g.roles))
        embed.add_field(name="Created", value=discord.utils.format_dt(g.created_at, "R"))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create a quick poll (up to 5 options)")
    @app_commands.describe(question="What to ask", options="Options separated by | e.g. pizza | tacos | sushi")
    @app_commands.guild_only()
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        choices = [o.strip() for o in options.split("|") if o.strip()][:5]
        if len(choices) < 2:
            return await interaction.response.send_message("give me at least 2 options separated by |", ephemeral=True)
        emojis = ["1\u20e3", "2\u20e3", "3\u20e3", "4\u20e3", "5\u20e3"]
        embed = discord.Embed(
            title=question,
            description="\n".join(f"{emojis[i]} {c}" for i, c in enumerate(choices)),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Poll by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(choices)):
            await msg.add_reaction(emojis[i])


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
