import datetime
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

NO_MENTIONS = discord.AllowedMentions.none()


class Quotes(commands.Cog):
    quote = app_commands.Group(name="quote", description="Save and recall memorable lines")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = sqlite3.connect("bot.db")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS quotes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, author_id INTEGER, "
            "saved_by INTEGER, text TEXT, ts TEXT)"
        )
        self.db.commit()

    async def cog_unload(self):
        self.db.close()

    @quote.command(name="add", description="Save a quote from a member")
    @app_commands.guild_only()
    @app_commands.describe(member="Who said it", text="The quote")
    async def add(self, interaction: discord.Interaction, member: discord.Member, text: app_commands.Range[str, 1, 300]):
        cur = self.db.execute(
            "INSERT INTO quotes (guild_id, author_id, saved_by, text, ts) VALUES (?,?,?,?,?)",
            (
                interaction.guild_id,
                member.id,
                interaction.user.id,
                text,
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ),
        )
        self.db.commit()
        await interaction.response.send_message(
            f"saved quote #{cur.lastrowid} from {member.display_name}.", allowed_mentions=NO_MENTIONS
        )

    @quote.command(name="random", description="Show a random saved quote")
    @app_commands.guild_only()
    @app_commands.describe(member="Only pick from this member's quotes (optional)")
    async def random_quote(self, interaction: discord.Interaction, member: discord.Member | None = None):
        if member:
            row = self.db.execute(
                "SELECT id, author_id, text, ts FROM quotes WHERE guild_id=? AND author_id=? "
                "ORDER BY RANDOM() LIMIT 1",
                (interaction.guild_id, member.id),
            ).fetchone()
        else:
            row = self.db.execute(
                "SELECT id, author_id, text, ts FROM quotes WHERE guild_id=? ORDER BY RANDOM() LIMIT 1",
                (interaction.guild_id,),
            ).fetchone()
        if not row:
            return await interaction.response.send_message("no quotes saved yet. use `/quote add`.", ephemeral=True)

        qid, author_id, text, ts = row
        embed = discord.Embed(description=f"\u201c{text}\u201d\n\u2014 <@{author_id}>", color=discord.Color.blurple())
        embed.set_footer(text=f"quote #{qid} - {ts[:10]}")
        await interaction.response.send_message(embed=embed, allowed_mentions=NO_MENTIONS)


async def setup(bot: commands.Bot):
    await bot.add_cog(Quotes(bot))
