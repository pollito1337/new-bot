import asyncio
import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("games")

NO_MENTIONS = discord.AllowedMentions.none()
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
ICONS = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}


class GiveawayView(discord.ui.View):
    def __init__(self, prize: str):
        super().__init__(timeout=None)
        self.prize = prize
        self.entrants: set[int] = set()

    @discord.ui.button(label="Enter", emoji="🎉", style=discord.ButtonStyle.primary)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.entrants:
            self.entrants.discard(interaction.user.id)
            await interaction.response.send_message("you left the giveaway.", ephemeral=True)
        else:
            self.entrants.add(interaction.user.id)
            await interaction.response.send_message("you're in. good luck.", ephemeral=True)


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks: set[asyncio.Task] = set()

    def cog_unload(self):
        for task in self._tasks:
            task.cancel()

    @app_commands.command(name="rps", description="Rock, paper, scissors against me")
    @app_commands.choices(
        move=[
            app_commands.Choice(name="rock", value="rock"),
            app_commands.Choice(name="paper", value="paper"),
            app_commands.Choice(name="scissors", value="scissors"),
        ]
    )
    async def rps(self, interaction: discord.Interaction, move: str):
        bot_move = random.choice(list(BEATS))
        if move == bot_move:
            verdict = "tie."
        elif BEATS[move] == bot_move:
            verdict = "you win."
        else:
            verdict = "i win."
        await interaction.response.send_message(f"you {ICONS[move]} vs me {ICONS[bot_move]}. {verdict}")

    @app_commands.command(name="mock", description="sPoNgEbOb-ify some text")
    @app_commands.describe(text="What to mock")
    async def mock(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, 300]):
        out = "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(text))
        await interaction.response.send_message(out, allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="giveaway", description="Start a giveaway with an Enter button")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(prize="What's being given away", minutes="How long it runs, 1 to 10080")
    async def giveaway(
        self,
        interaction: discord.Interaction,
        prize: app_commands.Range[str, 1, 100],
        minutes: app_commands.Range[int, 1, 10080],
    ):
        view = GiveawayView(prize)
        embed = discord.Embed(
            title="🎉 Giveaway",
            description=f"**Prize:** {prize}\nClick **Enter** to join. Ends in {minutes} min.",
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        task = asyncio.create_task(self._end_giveaway(message, view, minutes))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _end_giveaway(self, message: discord.Message, view: GiveawayView, minutes: int):
        await asyncio.sleep(minutes * 60)
        view.stop()
        for child in view.children:
            child.disabled = True

        winner = random.choice(list(view.entrants)) if view.entrants else None
        result = f"**Winner:** <@{winner}>" if winner else "No entries, so nobody won."
        embed = discord.Embed(
            title="🎉 Giveaway ended",
            description=f"**Prize:** {view.prize}\n{result}",
            color=discord.Color.greyple(),
        )
        try:
            await message.edit(embed=embed, view=view)
            if winner:
                await message.channel.send(
                    f"congrats <@{winner}>, you won **{view.prize}**!",
                    allowed_mentions=discord.AllowedMentions(
                        everyone=False, roles=False, users=[discord.Object(id=winner)]
                    ),
                )
        except discord.HTTPException:
            log.warning("couldn't finish giveaway")


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
