import ast
import asyncio
import datetime
import logging
import operator
import re
import secrets
import string

import discord
from discord import app_commands
from discord.ext import commands

from cogs.moderation import Moderation

log = logging.getLogger("tools")

NO_MENTIONS = discord.AllowedMentions.none()

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def safe_eval(expression: str):
    """Evaluate plain arithmetic only. No names, calls or attributes, so no code can run."""

    def _eval(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("exponent too large")
            return _BIN_OPS[type(node.op)](left, right)
        raise ValueError("unsupported expression")

    return _eval(ast.parse(expression, mode="eval").body)


class Tools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks: set[asyncio.Task] = set()

    def cog_unload(self):
        for task in self._tasks:
            task.cancel()

    @app_commands.command(name="calc", description="Do some math, e.g. (3+4)*2^3")
    @app_commands.describe(expression="Numbers with + - * / % ^ and brackets")
    async def calc(self, interaction: discord.Interaction, expression: app_commands.Range[str, 1, 100]):
        try:
            result = safe_eval(expression.replace("^", "**"))
        except ZeroDivisionError:
            return await interaction.response.send_message("can't divide by zero.", ephemeral=True)
        except (ValueError, SyntaxError, TypeError, OverflowError):
            return await interaction.response.send_message(
                "i can't work that out. plain numbers and + - * / % ^ only.", ephemeral=True
            )
        text = str(result)
        if len(text) > 1800:
            text = "result is too long to show."
        await interaction.response.send_message(f"`{expression}` = **{text}**")

    @app_commands.command(name="remind", description="Get pinged in this channel after a while")
    @app_commands.guild_only()
    @app_commands.describe(minutes="Wait time, 1 to 10080 (one week)", message="What to remind you about")
    async def remind(
        self,
        interaction: discord.Interaction,
        minutes: app_commands.Range[int, 1, 10080],
        message: app_commands.Range[str, 1, 300],
    ):
        await interaction.response.send_message(f"ok, i'll ping you in {minutes} min.", ephemeral=True)
        task = asyncio.create_task(self._remind_later(interaction.channel, interaction.user, minutes, message))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _remind_later(self, channel, user, minutes, message):
        await asyncio.sleep(minutes * 60)
        try:
            await channel.send(
                f"{user.mention} reminder: {message}",
                allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=[user]),
            )
        except discord.HTTPException:
            log.warning("couldn't send reminder for %s", user)

    @app_commands.command(name="timestamp", description="Make a Discord time stamp from a UTC date and time")
    @app_commands.describe(when="Format: YYYY-MM-DD HH:MM (UTC), e.g. 2026-12-25 18:00")
    async def timestamp(self, interaction: discord.Interaction, when: app_commands.Range[str, 1, 20]):
        try:
            dt = datetime.datetime.strptime(when.strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            return await interaction.response.send_message(
                "use the format `YYYY-MM-DD HH:MM` in UTC, like `2026-12-25 18:00`.", ephemeral=True
            )
        unix = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
        lines = [f"`<t:{unix}:{s}>` -> <t:{unix}:{s}>" for s in ("f", "F", "d", "D", "t", "T", "R")]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="color", description="Preview a hex color")
    @app_commands.describe(hex_code="e.g. #ff8800 or ff8800")
    async def color(self, interaction: discord.Interaction, hex_code: app_commands.Range[str, 1, 10]):
        code = hex_code.strip().lstrip("#")
        if len(code) == 3:
            code = "".join(c * 2 for c in code)
        if not re.fullmatch(r"[0-9a-fA-F]{6}", code):
            return await interaction.response.send_message(
                "that's not a valid hex color. try `#ff8800`.", ephemeral=True
            )
        value = int(code, 16)
        embed = discord.Embed(title=f"#{code.upper()}", color=value)
        embed.add_field(name="RGB", value=f"{(value >> 16) & 255}, {(value >> 8) & 255}, {value & 255}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="password", description="Generate a random password (only you can see it)")
    @app_commands.describe(length="Length, 8 to 64")
    async def password(self, interaction: discord.Interaction, length: app_commands.Range[int, 8, 64] = 20):
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        await interaction.response.send_message(f"||{pw}||", ephemeral=True)

    @app_commands.command(name="say", description="Make the bot say something")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(message="What to say", channel="Where to say it (default: this channel)")
    async def say(
        self,
        interaction: discord.Interaction,
        message: app_commands.Range[str, 1, 1900],
        channel: discord.TextChannel | None = None,
    ):
        target = channel or interaction.channel
        try:
            await target.send(message, allowed_mentions=NO_MENTIONS)
        except discord.Forbidden:
            return await interaction.response.send_message("i can't send messages there.", ephemeral=True)
        await interaction.response.send_message("sent.", ephemeral=True)

    @app_commands.command(name="slowmode", description="Set slowmode on this channel (0 turns it off)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.describe(seconds="Seconds between messages, 0 to 21600")
    async def slowmode(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
        await interaction.channel.edit(slowmode_delay=seconds, reason=f"{interaction.user}: slowmode")
        if seconds:
            await interaction.response.send_message(f"slowmode set to {seconds}s.")
        else:
            await interaction.response.send_message("slowmode off.")

    @app_commands.command(name="lock", description="Stop everyone from chatting in this channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        await self._set_lock(interaction, locked=True)

    @app_commands.command(name="unlock", description="Let everyone chat in this channel again")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        await self._set_lock(interaction, locked=False)

    async def _set_lock(self, interaction: discord.Interaction, locked: bool):
        channel = interaction.channel
        if isinstance(channel, discord.Thread):
            return await interaction.response.send_message(
                "i can't lock threads. lock the parent channel instead.", ephemeral=True
            )
        await channel.set_permissions(
            interaction.guild.default_role,
            send_messages=False if locked else None,
            reason=f"{interaction.user}: {'lock' if locked else 'unlock'}",
        )
        await interaction.response.send_message("🔒 channel locked." if locked else "🔓 channel unlocked.")

    @app_commands.command(name="nick", description="Change a member's nickname (leave name empty to reset)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.checks.has_permissions(manage_nicknames=True)
    @app_commands.checks.bot_has_permissions(manage_nicknames=True)
    @app_commands.describe(member="Who to rename", name="New nickname, max 32 characters")
    async def nick(self, interaction: discord.Interaction, member: discord.Member, name: str | None = None):
        if name and len(name) > 32:
            return await interaction.response.send_message("nicknames max out at 32 characters.", ephemeral=True)
        if err := Moderation._hierarchy_ok(interaction, member):
            return await interaction.response.send_message(err, ephemeral=True)
        await member.edit(nick=name or None, reason=f"{interaction.user}: nickname change")
        if name:
            await interaction.response.send_message(
                f"nickname for **{member}** is now **{name}**.", allowed_mentions=NO_MENTIONS
            )
        else:
            await interaction.response.send_message(f"reset **{member}**'s nickname.", allowed_mentions=NO_MENTIONS)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))
