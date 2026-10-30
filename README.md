# Discord Bot

discord.py 2.x, Python 3.10+. Slash commands, split into cogs.

## Commands
- **Utility:** /help /ping /avatar /userinfo /serverinfo /poll
- **Info:** /botinfo /snowflake /roles /emojis
- **Fun:** /8ball /roll /coinflip /choose /rps /mock /giveaway /reverse /emojify /ship /hug /joke /rate /wyr /fortune /compliment /clap
- **Tools:** /calc /remind /timestamp /color /password /convert /time /randnum
- **Text:** /morse /caesar /nato /wordcount /hash /base64 /uuid
- **To-do (private):** /todo add /todo list /todo done /todo remove
- **Birthdays:** /birthday set /birthday show /birthday remove /birthday list
- **Levels:** /rank /leaderboard (XP is earned by chatting, with a 60-second cooldown)
- **Music:** /join /leave /play /skip /stop /pause /resume /queue /nowplaying /volume /shuffle
- **Moderation:** /kick /ban /unban /timeout /untimeout /clear /warn /warnings /clearwarns /purge /slowmode /lock /unlock /nick
- **Admin:** /announce /role give /role take /invite /say
- **Quotes:** /quote add /quote random (saved in SQLite)
- **Suggestions:** /suggest (needs SUGGESTIONS_CHANNEL_ID in .env)
- **Welcome:** join message + optional auto-role

Reminders, giveaways, and the music queue live in memory, so they're lost if the bot restarts. To-dos, birthdays, XP, and quotes are saved in `bot.db`.

## Music notes
- `/play` accepts any http(s) link that points to audio or a live stream. The address doesn't need to end in .mp3 or any other extension. Uploaded audio files work too.
- Links to web pages (YouTube, Spotify, SoundCloud and similar) won't play, because those are pages, not audio. Bots that play them rely on tools that extract the audio, which breaks those services' terms, so that isn't included.
- Requires **FFmpeg** on your system:
  - Windows: `winget install Gyan.FFmpeg`, then restart your terminal
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

## Setup
1. Go to https://discord.com/developers/applications, create an application, and copy the bot token.
2. On the Bot page, enable **Server Members Intent**.
3. OAuth2 -> URL Generator: scopes `bot` + `applications.commands`. Permissions: Kick, Ban, Moderate Members, Manage Messages, Manage Roles, Manage Channels, Manage Nicknames, Manage Server, Create Invite, Send Messages, Embed Links, Add Reactions, Connect, Speak.
4. Put the bot's role **above** any role it needs to moderate or assign.

## Run
```bash
python -m venv .venv
.venv\Scripts\activate           # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp. Then add your token
python bot.py
```
Set `GUILD_ID` in `.env` while testing so slash commands appear instantly.

## Adding commands
Create `cogs/yourcog.py` with a `setup(bot)` function, then add `"cogs.yourcog"` to `EXTENSIONS` in `bot.py`. Discord allows up to 100 top-level slash commands per application; this bot has about 78.
