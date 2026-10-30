import hashlib
import uuid

import discord
from discord import app_commands
from discord.ext import commands

NO_MENTIONS = discord.AllowedMentions.none()

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....",
    "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.",
    "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.", ".": ".-.-.-", ",": "--..--",
    "?": "..--..", "!": "-.-.--",
}
REVERSE_MORSE = {code: letter for letter, code in MORSE.items()}

NATO = {
    "A": "Alfa", "B": "Bravo", "C": "Charlie", "D": "Delta", "E": "Echo", "F": "Foxtrot", "G": "Golf",
    "H": "Hotel", "I": "India", "J": "Juliett", "K": "Kilo", "L": "Lima", "M": "Mike", "N": "November",
    "O": "Oscar", "P": "Papa", "Q": "Quebec", "R": "Romeo", "S": "Sierra", "T": "Tango", "U": "Uniform",
    "V": "Victor", "W": "Whiskey", "X": "X-ray", "Y": "Yankee", "Z": "Zulu",
    "0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six",
    "7": "Seven", "8": "Eight", "9": "Nine",
}


def to_morse(text: str) -> str:
    encoded = []
    for word in text.upper().split():
        codes = [MORSE[ch] for ch in word if ch in MORSE]
        if codes:
            encoded.append(" ".join(codes))
    return " / ".join(encoded)


def from_morse(code: str) -> str:
    words = []
    for word in code.strip().split(" / "):
        letters = []
        for symbol in word.split():
            if symbol not in REVERSE_MORSE:
                raise ValueError(f"unknown morse code: {symbol}")
            letters.append(REVERSE_MORSE[symbol])
        if letters:
            words.append("".join(letters))
    return " ".join(words)


def caesar(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if "a" <= ch <= "z" or "A" <= ch <= "Z":
            base = ord("a") if ch.islower() else ord("A")
            out.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            out.append(ch)
    return "".join(out)


def to_nato(text: str) -> str:
    words = []
    for ch in text.upper():
        if ch in NATO:
            words.append(NATO[ch])
        elif ch == " ":
            words.append("|")
    return " ".join(words)


class Text(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="morse", description="Encode or decode Morse code")
    @app_commands.describe(mode="encode or decode", text="The text to convert")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="encode", value="encode"),
            app_commands.Choice(name="decode", value="decode"),
        ]
    )
    async def morse_cmd(self, interaction: discord.Interaction, mode: str, text: app_commands.Range[str, 1, 500]):
        if mode == "encode":
            result = to_morse(text)
        else:
            try:
                result = from_morse(text)
            except ValueError as e:
                return await interaction.response.send_message(str(e), ephemeral=True)
        if not result:
            return await interaction.response.send_message("nothing to convert there.", ephemeral=True)
        await interaction.response.send_message(f"```\n{result}\n```", allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="caesar", description="Shift letters by a number (a Caesar cipher)")
    @app_commands.describe(text="The text", shift="How far to shift, -25 to 25")
    async def caesar_cmd(
        self,
        interaction: discord.Interaction,
        text: app_commands.Range[str, 1, 500],
        shift: app_commands.Range[int, -25, 25],
    ):
        await interaction.response.send_message(caesar(text, shift), allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="nato", description="Spell text with the NATO phonetic alphabet")
    @app_commands.describe(text="Letters and numbers")
    async def nato_cmd(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, 100]):
        result = to_nato(text)
        if not result:
            return await interaction.response.send_message("use letters or numbers.", ephemeral=True)
        await interaction.response.send_message(result, allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="wordcount", description="Count words, letters and characters")
    @app_commands.describe(text="The text to count")
    async def wordcount_cmd(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, 2000]):
        embed = discord.Embed(title="Word count", color=discord.Color.blurple())
        embed.add_field(name="Words", value=str(len(text.split())))
        embed.add_field(name="Characters", value=str(len(text)))
        embed.add_field(name="Letters", value=str(sum(c.isalpha() for c in text)))
        embed.add_field(name="Lines", value=str(text.count("\n") + 1))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hash", description="Hash some text")
    @app_commands.describe(algorithm="Which hash to use", text="The text to hash")
    @app_commands.choices(
        algorithm=[
            app_commands.Choice(name="md5", value="md5"),
            app_commands.Choice(name="sha1", value="sha1"),
            app_commands.Choice(name="sha256", value="sha256"),
            app_commands.Choice(name="sha512", value="sha512"),
        ]
    )
    async def hash_cmd(self, interaction: discord.Interaction, algorithm: str, text: app_commands.Range[str, 1, 1000]):
        digest = hashlib.new(algorithm, text.encode("utf-8")).hexdigest()
        await interaction.response.send_message(f"**{algorithm}**\n```\n{digest}\n```", allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="uuid", description="Generate a random UUID")
    async def uuid_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"`{uuid.uuid4()}`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Text(bot))
