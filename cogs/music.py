import asyncio
import ipaddress
import logging
import random
from collections import deque
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("music")

NO_MENTIONS = discord.AllowedMentions.none()
FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


def is_blocked_host(host: str) -> bool:
    """Block localhost and private/internal IP addresses typed in directly."""
    if host.lower() == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # a domain name; we only check literal addresses here
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


PAGE_ONLY_SITES = ("youtube.com", "youtu.be", "spotify.com", "soundcloud.com", "music.apple.com")


def is_page_only_site(host: str) -> bool:
    """These sites serve web pages, not audio, so their links can't be played."""
    host = host.lower()
    return any(host == site or host.endswith("." + site) for site in PAGE_ONLY_SITES)


async def probe_url(url: str) -> str | None:
    """Ask the server what it sends back. Returns an error message, or None if it looks playable."""
    timeout = aiohttp.ClientTimeout(total=8)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status >= 400:
                    return f"that link returned an error ({resp.status})."
                content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return "i couldn't reach that link."
    if content_type in ("text/html", "application/xhtml+xml", "application/json"):
        return "that link is a web page, not audio. try a direct audio or stream link."
    return None


@dataclass
class Track:
    title: str
    source: str  # any http(s) URL that FFmpeg can read as audio, or a Discord attachment URL
    requester: str


class GuildPlayer:
    def __init__(self):
        self.queue: deque[Track] = deque()
        self.current: Track | None = None
        self.volume = 0.5


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    async def cog_unload(self):
        for vc in list(self.bot.voice_clients):
            await vc.disconnect(force=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # if the bot gets disconnected, forget its queue
        if member.id == self.bot.user.id and after.channel is None:
            self.players.pop(member.guild.id, None)

    # ---------- playback engine ----------

    def _player(self, guild_id: int) -> GuildPlayer:
        return self.players.setdefault(guild_id, GuildPlayer())

    async def _play_next(self, guild: discord.Guild):
        player = self.players.get(guild.id)
        vc = guild.voice_client
        if player is None or vc is None or not vc.is_connected():
            return
        while player.queue:
            track = player.queue.popleft()
            try:
                source = discord.FFmpegPCMAudio(track.source, **FFMPEG_OPTS)
            except Exception:
                log.exception("couldn't start %s", track.title)
                continue
            player.current = track
            audio = discord.PCMVolumeTransformer(source, volume=player.volume)
            try:
                vc.play(audio, after=lambda err, g=guild: self._after_track(g, err))
            except discord.ClientException:
                log.exception("already playing when starting %s", track.title)
            return
        player.current = None

    def _after_track(self, guild: discord.Guild, error: Exception | None):
        # this runs on the audio thread, so hand the next track to the event loop
        if error:
            log.warning("playback error: %s", error)
        asyncio.run_coroutine_threadsafe(self._play_next(guild), self.bot.loop)

    async def _ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        vc = interaction.guild.voice_client
        if vc and vc.is_connected():
            return vc
        voice = interaction.user.voice
        if not voice or not voice.channel:
            return None
        try:
            return await voice.channel.connect()
        except (discord.ClientException, asyncio.TimeoutError, discord.HTTPException):
            log.exception("couldn't join voice channel")
            return None

    # ---------- commands ----------

    @app_commands.command(name="join", description="Join your voice channel")
    @app_commands.guild_only()
    async def join(self, interaction: discord.Interaction):
        voice = interaction.user.voice
        if not voice or not voice.channel:
            return await interaction.response.send_message("join a voice channel first.", ephemeral=True)
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc:
            await vc.move_to(voice.channel)
        else:
            await voice.channel.connect()
        await interaction.followup.send(f"joined **{voice.channel.name}**.")

    @app_commands.command(name="leave", description="Leave voice and clear the queue")
    @app_commands.guild_only()
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("i'm not in a voice channel.", ephemeral=True)
        self.players.pop(interaction.guild_id, None)
        await vc.disconnect()
        await interaction.response.send_message("left the voice channel.")

    @app_commands.command(name="play", description="Play audio from a URL or an uploaded file")
    @app_commands.guild_only()
    @app_commands.describe(url="A link to audio or a stream (any address, no file ending needed)", upload="Or upload an audio file")
    async def play(
        self,
        interaction: discord.Interaction,
        url: str | None = None,
        upload: discord.Attachment | None = None,
    ):
        if url is None and upload is None:
            return await interaction.response.send_message(
                "give me a url or upload an audio file.", ephemeral=True
            )

        if upload is not None:
            if upload.content_type and upload.content_type.split("/")[0] not in ("audio", "video"):
                return await interaction.response.send_message("that file doesn't look like audio.", ephemeral=True)
            source, title = upload.url, upload.filename
        else:
            url = url.strip()
            parsed = urlparse(url)
            # only web addresses; FFmpeg also understands file:// and other protocols, so block those
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                return await interaction.response.send_message(
                    "links must start with http:// or https://.", ephemeral=True
                )
            if is_blocked_host(parsed.hostname):
                return await interaction.response.send_message("that address isn't allowed.", ephemeral=True)
            if is_page_only_site(parsed.hostname):
                return await interaction.response.send_message(
                    "YouTube, Spotify, SoundCloud and Apple Music links are web pages, not audio, "
                    "so i can't play them. try a direct audio link or upload a file.",
                    ephemeral=True,
                )
            source = url
            title = unquote(parsed.path.rsplit("/", 1)[-1]) or parsed.hostname

        await interaction.response.defer()

        if upload is None:
            problem = await probe_url(source)
            if problem:
                return await interaction.followup.send(problem, ephemeral=True)

        vc = await self._ensure_voice(interaction)
        if vc is None:
            return await interaction.followup.send(
                "join a voice channel first, then try again.", ephemeral=True
            )

        player = self._player(interaction.guild_id)
        player.queue.append(Track(title, source, interaction.user.display_name))

        if vc.is_playing() or vc.is_paused():
            return await interaction.followup.send(
                f"queued **{title}** at #{len(player.queue)}.", allowed_mentions=NO_MENTIONS
            )

        await self._play_next(interaction.guild)
        if player.current is None:
            return await interaction.followup.send(
                "couldn't start that one. is FFmpeg installed?", allowed_mentions=NO_MENTIONS
            )
        await interaction.followup.send(
            f"now playing **{player.current.title}**.", allowed_mentions=NO_MENTIONS
        )

    @app_commands.command(name="skip", description="Skip the current track")
    @app_commands.guild_only()
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await interaction.response.send_message("nothing is playing.", ephemeral=True)
        vc.stop()  # the after-callback starts the next track
        await interaction.response.send_message("skipped.")

    @app_commands.command(name="stop", description="Stop playback and clear the queue")
    @app_commands.guild_only()
    async def stop(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild_id)
        if player:
            player.queue.clear()
            player.current = None
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
        await interaction.response.send_message("stopped and cleared the queue.")

    @app_commands.command(name="pause", description="Pause playback")
    @app_commands.guild_only()
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("nothing is playing.", ephemeral=True)
        vc.pause()
        await interaction.response.send_message("paused.")

    @app_commands.command(name="resume", description="Resume playback")
    @app_commands.guild_only()
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_paused():
            return await interaction.response.send_message("nothing is paused.", ephemeral=True)
        vc.resume()
        await interaction.response.send_message("resumed.")

    @app_commands.command(name="nowplaying", description="Show the current track")
    @app_commands.guild_only()
    async def nowplaying(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.current:
            return await interaction.response.send_message("nothing is playing.", ephemeral=True)
        track = player.current
        await interaction.response.send_message(
            f"now playing **{track.title}** (requested by {track.requester})", allowed_mentions=NO_MENTIONS
        )

    @app_commands.command(name="queue", description="Show what's playing and what's next")
    @app_commands.guild_only()
    async def queue(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or (not player.current and not player.queue):
            return await interaction.response.send_message("the queue is empty.", ephemeral=True)
        lines = []
        if player.current:
            lines.append(f"**Now:** {player.current.title} (requested by {player.current.requester})")
        upcoming = list(player.queue)
        for i, track in enumerate(upcoming[:10], 1):
            lines.append(f"`{i}.` {track.title} (requested by {track.requester})")
        if len(upcoming) > 10:
            lines.append(f"...and {len(upcoming) - 10} more")
        embed = discord.Embed(title="Queue", description="\n".join(lines), color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="volume", description="Set playback volume (default 50)")
    @app_commands.guild_only()
    @app_commands.describe(level="0 to 200")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 200]):
        player = self._player(interaction.guild_id)
        player.volume = level / 100
        vc = interaction.guild.voice_client
        if vc and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = player.volume  # applies to the track that's already playing
        await interaction.response.send_message(f"volume set to {level}%.")

    @app_commands.command(name="shuffle", description="Shuffle the queue")
    @app_commands.guild_only()
    async def shuffle(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or len(player.queue) < 2:
            return await interaction.response.send_message(
                "need at least two tracks in the queue to shuffle.", ephemeral=True
            )
        items = list(player.queue)
        random.shuffle(items)
        player.queue = deque(items)
        await interaction.response.send_message(f"shuffled {len(items)} tracks.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
