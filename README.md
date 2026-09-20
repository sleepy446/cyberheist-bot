# 🕵️ CyberHeist Bot

**CyberHeist Bot** adalah bot Discord idle/incremental game dengan tema peretasan siber. Player bisa:
- 💻 Meretas server kecil untuk mendapat **Bytes** (currency) dan **XP**
- 🔥 Mengelola **Heat** (tingkat buronan) sebelum tertangkap
- ⚙️ Membeli **hardware/rig** untuk passive income
- 📊 Bersaing di **leaderboard** global

---

## 🚀 Setup & Installation

### 1. Clone Repository
```bash
git clone <repo-url>
cd cyberheist-bot
```

### 2. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Setup Discord Bot Token
1. Pergi ke [Discord Developer Portal](https://discord.com/developers/applications)
2. Buat aplikasi baru → Tab "Bot" → Copy token
3. Aktifkan **Message Content Intent** di tab "Bot"
4. Copy file `.env.example` jadi `.env`:
   ```bash
   cp .env.example .env
   ```
5. Edit `.env` dan isi token kamu:
   ```env
   DISCORD_TOKEN=your_actual_token_here
   ```

### 4. Invite Bot ke Server
1. Tab "OAuth2" → "URL Generator"
2. Pilih scope: `bot` dan `applications.commands`
3. Pilih permissions: `Send Messages`, `Embed Links`, `Read Message History`
4. Copy URL dan buka di browser untuk invite bot

### 5. Jalankan Bot
```bash
python main.py
```

Jika berhasil, kamu akan lihat log:
```
[2026-09-20 12:00:00] [ INFO   ] __main__: Bot berhasil online sebagai: YourBotName#1234
[2026-09-20 12:00:00] [ INFO   ] __main__: CyberHeist Bot siap menerima command!
```

---

## 🎮 Player Commands

| Command | Aliases | Deskripsi |
|---------|---------|-----------|
| `!hack` | - | Meretas target random untuk dapet Bytes & XP (cooldown: 4 detik) |
| `!profile` | `!stats` | Lihat status player: Level, Bytes, XP, Heat, Rig |
| `!leaderboard` | `!lb`, `!top` | Papan peringkat top 10 hacker terkaya |
| `!shop` | `!blackmarket`, `!store` | Lihat daftar hardware/rig yang bisa dibeli |
| `!buy <tier>` | - | Beli hardware (contoh: `!buy 1`) |
| `!net` | `!mine`, `!claim` | Klaim passive income dari rig (cooldown: 5 menit) |
| `!clean` | `!wash`, `!laylow` | Kurangi Heat dengan bayar Bytes (cooldown: 3 menit) |
| `!help` | - | Tampilkan list command |
| `!ping` | - | Tes koneksi bot |

---

## 🔧 Admin Commands

**Catatan:** Command ini HANYA bisa digunakan oleh Owner bot (akun yang membuat Discord Application).

| Command | Deskripsi |
|---------|-----------|
| `!ahelp` | Lihat semua admin command |
| `!unjail @user` | Batalkan status jail player |
| `!addbytes @user <amount>` | Tambah/kurangi Bytes player |
| `!setbytes @user <amount>` | Set Bytes player langsung |
| `!addxp @user <amount>` | Tambah XP player (auto level up) |
| `!setlevel @user <level>` | Set Level player langsung |
| `!setheat @user <0-100>` | Set Heat player (tanpa trigger jail) |
| `!setrig @user <tier>` | Set rig_level player |
| `!resetplayer @user confirm` | Hapus SEMUA data player |
| `!playerinfo [@user]` | Lihat raw data player dari database |
| `!dbstats` | Statistik ekonomi server (total player, Bytes, dll) |
| `!reload <cog_name>` | Reload cog tanpa restart bot (dev tool) |

---

## ⚙️ Game Mechanics

### 💰 Bytes (Currency)
- Didapat dari `!hack` (20-60 per hack) dan `!net` (tergantung rig tier)
- Digunakan untuk beli hardware dan bayar `!clean`
- Bisa disita saat arrested (35% dari total)

### ⚡ XP & Leveling
- Didapat dari `!hack` (15-35 XP per hack)
- XP requirement naik eksponensial: `50 * (level ^ 1.5)`
- Level meningkatkan biaya `!clean` tapi juga prestige

### 🔥 Heat System
- Setiap `!hack` menambah **+8 Heat**
- Heat > 70 = risiko gagal hack naik ke **35%**
- Heat mencapai 100 = **ARRESTED**:
  - Bytes disita 35% (min 50 Bytes)
  - Tidak bisa `!hack` selama 5 menit
  - Heat reset ke 0
- Heat decay pasif: **-5 poin/menit** otomatis

### ⚙️ Hardware/Rig Tiers
| Tier | Nama | Harga | Passive Income (per `!net`) |
|------|------|-------|------------------------------|
| 1 | Botnet Kecil | 500 Bytes | +5 Bytes |
| 2 | GPU Rig | 2,500 Bytes | +30 Bytes |
| 3 | Server Rack | 10,000 Bytes | +150 Bytes |

---

## 📁 Project Structure

```
cyberheist-bot/
├── main.py              # Entry point bot
├── config.py            # Balancing & game constants
├── database.py          # Database layer (SQLite)
├── logger.py            # Logging configuration
├── requirements.txt     # Python dependencies
├── .env                 # Token (JANGAN commit!)
├── .env.example         # Template untuk .env
├── .gitignore           # Git ignore rules
├── README.md            # Dokumentasi (file ini)
├── changelog.md         # Development notes
├── cogs/                # Command modules
│   ├── __init__.py
│   ├── hack.py          # !hack command
│   ├── profile.py       # !profile, !leaderboard
│   ├── shop.py          # !shop, !buy
│   ├── net.py           # !net command
│   ├── clean.py         # !clean command
│   ├── admin.py         # Admin commands
│   ├── help.py          # !help, !ahelp
│   └── tasks.py         # Background tasks (heat decay)
├── data/                # Database files
│   └── cyberheist.sqlite3
└── logs/                # Log files (auto-created)
    └── cyberheist.log
```

---

## 🐛 Known Issues & Fixes

✅ **FIXED (2026-09-20):**
- Race condition di database operations
- Bytes bisa jadi negatif
- Shop hardcode vs config mismatch
- Help command detection fragile
- Clean footer salah tulis cooldown
- Tidak ada global error handler
- Database path relatif ke CWD

📋 **Planned Features:** Lihat `CYBERHEIST_FEATURE_SUGGESTIONS.txt` di home directory

---

## 🔐 Security Notes

- **JANGAN** commit file `.env` ke Git (sudah ada di `.gitignore`)
- **JANGAN** share Discord bot token ke siapapun
- Kalau token bocor, regenerate di Discord Developer Portal
- Database (`data/*.sqlite3`) juga di-gitignore untuk privasi player

---

## 🤝 Contributing

1. Fork repository
2. Buat branch baru: `git checkout -b feature/nama-fitur`
3. Commit changes: `git commit -m "Add: fitur X"`
4. Push ke branch: `git push origin feature/nama-fitur`
5. Buat Pull Request

---

## 📝 License

Project ini dibuat untuk pembelajaran dan fun. Silakan modifikasi sesuai kebutuhan.

---

## 💬 Support

Jika ada bug atau pertanyaan, buka Issue di GitHub atau hubungi maintainer.

**Happy Hacking! 🕵️‍♂️💻**
