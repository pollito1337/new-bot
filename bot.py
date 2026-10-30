"""Discord bot - discord.py 2.x, Python 3.10+
Run: python bot.py
"""
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

intents = discord.Intents.default()
intents.members = True  # privileged: enable "Server Members Intent" in the dev portal

EXTENSIONS = ("cogs.utility", "cogs.fun", "cogs.moderation", "cogs.welcome", "cogs.tools", "cogs.games", "cogs.quotes", "cogs.music", "cogs.extras", "cogs.levels", "cogs.personal", "cogs.misc", "cogs.admin", "cogs.info", "cogs.text", "cogs.entertainment", "cogs.birthdays")


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned, intents=intents, help_command=None)

    async def setup_hook(self):
        for ext in EXTENSIONS:
            await self.load_extension(ext)
            log.info("loaded %s", ext)

        self.tree.on_error = self.on_tree_error

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("synced commands to guild %s", GUILD_ID)
        else:
            await self.tree.sync()
            log.info("synced commands globally")

    async def on_ready(self):
        log.info("logged in as %s (%s)", self.user, self.user.id)
        await self.change_presence(activity=discord.Game(name="/help"))

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "you don't have permission to do that."
        elif isinstance(error, app_commands.BotMissingPermissions):
            msg = "i'm missing permissions for that. check my role."
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"slow down. try again in {error.retry_after:.1f}s."
        else:
            msg = "something broke. check the logs."
            log.exception("command error", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


def main():
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN missing. copy .env.example to .env and fill it in.")
    Bot().run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
