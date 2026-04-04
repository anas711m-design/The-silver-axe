# AntiDisconnect Bot

A Discord bot that temporarily removes the mod role from anyone who disconnects another member from a voice channel.

## How It Works
- Listens for voice disconnects
- Checks audit logs to find who triggered the disconnect
- Removes their mod role for 2 minutes as a penalty
- Automatically restores the role after the penalty

## Setup

1. Copy `.env.example` to `.env` and fill in your token:
DISCORD_TOKEN=your_token_here

2. Install dependencies:
pip install -r requirements.txt

3. Edit `config.py` and set your `MOD_ROLE_ID`

4. Run the bot:
python main.py

## File Structure
- `main.py` — starts the bot and loads cogs
- `config.py` — all settings (role ID, penalty time)
- `cogs/voice_guard.py` — the voice disconnect logic
- `requirements.txt` — Python dependencies
- `Procfile` — tells Railway how to run the bot
