# Discord Crypto Monitor

A Discord bot that monitors the top 6 cryptocurrencies and updates a single embed message in real time using the CoinGecko public API.

Monitored coins: BTC, ETH, SOL, BNB, XRP, ADA.

---

## Requirements

- Docker
- Docker Compose
- A Discord bot token

---

## Installing Docker

### Windows

1. Download Docker Desktop from https://www.docker.com/products/docker-desktop
2. Run the installer and follow the setup wizard
3. Start Docker Desktop
4. Open PowerShell and verify:
   ```
   docker --version
   docker compose version
   ```

### macOS

1. Download Docker Desktop from https://www.docker.com/products/docker-desktop
2. Open the .dmg file and drag Docker to Applications
3. Launch Docker from Applications
4. Open Terminal and verify:
   ```
   docker --version
   docker compose version
   ```

### Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

Verify:
```bash
docker --version
docker compose version
```

---

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/mtddbxhgq/crypto-monitor-discord-bot.git
   cd crypto-monitor-discord-bot
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Fill in the values in `.env`:
   ```
   DISCORD_TOKEN=your_bot_token
   CHANNEL_ID=your_channel_id
   UPDATE_INTERVAL=30
   ```

   - `DISCORD_TOKEN` — get it from https://discord.com/developers/applications
   - `CHANNEL_ID` — right-click a channel in Discord and select Copy Channel ID
   - `UPDATE_INTERVAL` — seconds between updates (minimum 15)

4. Start the bot:
   ```bash
   sudo docker-compose up -d
   ```
    ```Windows, Before doing that, you need to run Docker Desktop.
    docker-compose up -d
   ``

---

## Discord Bot Setup

1. Go to https://discord.com/developers/applications
2. Create a New Application
3. Go to Bot section, click Reset Token and copy it
4. Enable Message Content Intent under Privileged Gateway Intents
5. Go to OAuth2 > URL Generator
6. Select scopes: `bot`
7. Select permissions: `Send Messages`, `Read Message History`, `Embed Links`
8. Open the generated URL and invite the bot to your server

---

## Commands

```bash
# View logs
sudo docker-compose logs -f

# Stop the bot
sudo docker-compose down

# Restart the bot
sudo docker-compose restart
```

---

## Security

- Never commit your `.env` file — it is listed in `.gitignore`
- The bot runs as a non-root user inside the container
- Only `.env.example` (with no real values) is safe to commit
