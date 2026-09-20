# CyberHeist Bot

A Discord idle/incremental game bot with a cybercrime theme. Players hack servers, manage their heat level, upgrade hardware for passive income, and compete on a global leaderboard.

## Features

- Manual grinding via hacking command with random rewards
- Heat system with arrest mechanics and jail time
- Hardware/rig upgrades for passive income
- XP and leveling with exponential scaling
- Global leaderboard across all servers
- Admin tools for testing and moderation

## Requirements

- Python 3.8 or higher
- Discord bot token with Message Content Intent enabled
- SQLite3 (included with Python)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sleepy446/cyberheist-bot.git
cd cyberheist-bot
```

### 2. Set up virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and edit it with your bot token:

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

Add your Discord bot token:

```env
DISCORD_TOKEN=your_actual_token_here
```

### 4. Create Discord application

1. Go to https://discord.com/developers/applications
2. Create a new application
3. Navigate to the "Bot" tab and create a bot
4. Copy the token and paste it into your `.env` file
5. Enable "Message Content Intent" under Privileged Gateway Intents
6. Go to OAuth2 > URL Generator
7. Select scopes: `bot` and `applications.commands`
8. Select bot permissions: `Send Messages`, `Embed Links`, `Read Message History`
9. Use the generated URL to invite the bot to your server

### 5. Run the bot

```bash
python main.py
```

If successful, you should see:

```
[2026-09-20 12:00:00] [ INFO   ] __main__: Bot berhasil online sebagai: YourBotName#1234
[2026-09-20 12:00:00] [ INFO   ] __main__: CyberHeist Bot siap menerima command!
```

## Commands

### Player Commands (Slash Commands)

All player commands use Discord **Slash Commands** (`/`):

| Command | Description |
|---------|-------------|
| `/hack` | Hack a random target for Bytes and XP (4 second cooldown) |
| `/profile` | View your stats: level, Bytes, XP, Heat, hardware, and daily streak |
| `/leaderboard` | Show top 10 wealthiest hackers |
| `/shop` | View available hardware for purchase |
| `/buy <tier>` | Purchase hardware with dynamic autocomplete (example: `/buy 1`) |
| `/net` | Claim passive income from your rig (5 minute cooldown) |
| `/clean` | Reduce Heat by paying Bytes (3 minute cooldown) |
| `/daily` | Claim daily reward with streak bonus and mystery drops (resets 00:00 UTC) |
| `/ping` | Check bot latency |
| `/help` | Display list of player slash commands |

### Admin Commands (Prefix Commands)

Available only to the bot owner using standard prefix (`!`):

| Command | Description |
|---------|-------------|
| `!ahelp` | View all admin commands |
| `!sync [guild]` | Sync slash commands tree globally or locally to current guild |
| `!unjail @user` | Remove jail status from a player |
| `!addbytes @user <amount>` | Add or subtract Bytes (negative values allowed) |
| `!setbytes @user <amount>` | Set player Bytes to a specific value |
| `!addxp @user <amount>` | Add XP to a player (auto-processes level ups) |
| `!setlevel @user <level>` | Set player level directly |
| `!setheat @user <0-100>` | Set player Heat without triggering jail |
| `!setrig @user <tier>` | Set player rig level directly |
| `!resetdaily [@user]` | Reset daily claim status for testing |
| `!setstreak @user <days>` | Set player daily streak to specific value |
| `!resetplayer @user confirm` | Delete all player data (requires confirmation) |
| `!playerinfo [@user]` | View raw database data for a player |
| `!dbstats` | View economy statistics (total players, Bytes, etc) |
| `!reload <cog_name>` | Reload a cog without restarting the bot |

## Game Mechanics

### Currency: Bytes

- Earned from `!hack` (20-60 per hack) and `!net` (depends on rig tier)
- Used to purchase hardware and pay for `!clean`
- Can be confiscated during arrest (35% of total)

### XP and Leveling

- Gained from `!hack` (15-35 XP per hack)
- XP requirement increases exponentially: `50 * (level ^ 1.5)`
- Higher level increases `!clean` cost but also prestige

### Heat System

- Every successful `!hack` adds +8 Heat
- Heat above 70 increases hack failure chance to 35%
- Reaching 100 Heat triggers arrest:
  - 35% of Bytes confiscated (minimum 50 Bytes)
  - Cannot hack for 5 minutes
  - Heat reset to 0
- Passive decay: -5 Heat per minute automatically

### Hardware Tiers

| Tier | Name | Price | Passive Income per `!net` |
|------|------|-------|---------------------------|
| 1 | Botnet Kecil | 450 Bytes | +5 Bytes |
| 2 | GPU Rig | 2,500 Bytes | +30 Bytes |
| 3 | Server Rack | 10,000 Bytes | +150 Bytes |

### Daily Reward System

- Available every 24 hours (resets at 00:00 UTC)
- **Base Reward:** 100-200 Bytes (guaranteed)
- **Streak Bonus:** +10 Bytes per consecutive day, capped at 100 Bytes max (reached on day 10)
- **Mystery Drop Pool** (one random bonus):
  - 40% Extra Bytes: +25 to +50 Bytes
  - 30% Bonus XP: +20 to +40 XP (auto-processes level ups)
  - 20% Heat Reduction: -10 to -20 Heat
  - 10% Encrypted Master Key: +15 to +30 Bytes
- **Streak Rules:**
  - Claim daily to maintain streak
  - Missing a day resets streak to 1
  - View current streak in `!profile`

## Project Structure

```
cyberheist-bot/
├── main.py              # Bot entry point
├── config.py            # Game balancing constants
├── database.py          # Database layer (SQLite)
├── logger.py            # Logging configuration
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not committed)
├── .env.example         # Environment variable template
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── changelog.md         # Development notes
├── cogs/                # Command modules
│   ├── __init__.py
│   ├── hack.py          # Hack command
│   ├── profile.py       # Profile and leaderboard
│   ├── shop.py          # Shop and buy commands
│   ├── net.py           # Passive income claim
│   ├── clean.py         # Heat reduction
│   ├── daily.py         # Daily reward system
│   ├── admin.py         # Admin commands
│   ├── help.py          # Help commands
│   └── tasks.py         # Background tasks (heat decay)
├── data/                # Database files
│   └── cyberheist.sqlite3
└── logs/                # Log files (auto-created)
    └── cyberheist.log
```

## Configuration

All game balancing values are stored in `config.py`:

- XP curve parameters
- Heat gain/reduction rates
- Arrest penalties
- Hardware tier prices and income
- Cooldown durations

Modify these values to rebalance the game without touching the core logic.

## Logging

The bot uses a rotating file handler that:

- Writes logs to `logs/cyberheist.log`
- Rotates at 5MB with 5 backup files (max 25MB total)
- Outputs INFO level and above to console
- Outputs DEBUG level and above to file

## Security Notes

- Never commit your `.env` file to version control
- Never share your Discord bot token
- If your token is compromised, regenerate it in the Discord Developer Portal
- Database files (`data/*.sqlite3`) are gitignored to protect player privacy

## Database

The bot uses SQLite with a single `players` table. Data is global (one wallet per Discord user ID) across all servers.

### Schema

```sql
CREATE TABLE players (
    user_id     INTEGER PRIMARY KEY,
    bytes       INTEGER NOT NULL DEFAULT 0,
    level       INTEGER NOT NULL DEFAULT 1,
    xp          INTEGER NOT NULL DEFAULT 0,
    heat        INTEGER NOT NULL DEFAULT 0,
    rig_level   INTEGER NOT NULL DEFAULT 0,
    jail_until  INTEGER NOT NULL DEFAULT 0
);
```

## Development

### Hot Reload

Use the `!reload <cog_name>` command to reload a single cog without restarting the bot:

```
!reload hack
!reload shop
```

### Adding New Commands

1. Create or edit a file in `cogs/`
2. Add the cog name to `INITIAL_EXTENSIONS` in `main.py`
3. Use `!reload <cog_name>` to load it without restarting

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

## Known Issues

All critical bugs have been fixed as of the latest commit. See changelog.md for details.

## License

This project is created for educational and entertainment purposes. Feel free to modify and use as needed.

## Support

For bugs or questions, open an issue on GitHub or contact the maintainer.
