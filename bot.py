import os
import json
import asyncio
from datetime import datetime, timezone

import discord
import websockets
from dotenv import load_dotenv


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "5"))

if UPDATE_INTERVAL < 5:
    UPDATE_INTERVAL = 5


COINS = [
    {"symbol": "BTC", "stream": "btcusdt"},
    {"symbol": "ETH", "stream": "ethusdt"},
    {"symbol": "SOL", "stream": "solusdt"},
    {"symbol": "BNB", "stream": "bnbusdt"},
    {"symbol": "XRP", "stream": "xrpusdt"},
    {"symbol": "ADA", "stream": "adausdt"},
]

STREAM_TO_SYMBOL = {
    coin["stream"]: coin["symbol"]
    for coin in COINS
}

prices = {
    coin["symbol"]: {
        "price": 0.0,
        "display_prev": 0.0,
        "change": 0.0,
        "volume": 0.0,
    }
    for coin in COINS
}

price_lock = asyncio.Lock()

intents = discord.Intents.default()
client = discord.Client(intents=intents)

monitor_message: discord.Message | None = None
tasks_started = False


def format_price(price: float, symbol: str) -> str:
    if price <= 0:
        return "—"

    if symbol in ("XRP", "ADA"):
        return f"${price:.4f}"

    return f"${price:,.2f}"


def format_volume(volume: float) -> str:
    if volume <= 0:
        return "—"

    if volume >= 1_000_000_000:
        return f"${volume / 1_000_000_000:.2f}B"

    return f"${volume / 1_000_000:.1f}M"


def get_market_color(snapshot: dict) -> discord.Color:
    positive = sum(
        1 for data in snapshot.values()
        if data["change"] >= 0
    )

    if positive >= 4:
        return discord.Color.green()

    if positive <= 2:
        return discord.Color.red()

    return discord.Color.orange()


def get_change_text(change: float) -> str:
    if change > 0:
        return f"+{change:.2f}%"

    if change < 0:
        return f"{change:.2f}%"

    return "0.00%"


def get_status_icon(change: float) -> str:
    if change > 0:
        return "🟢 ▲"

    if change < 0:
        return "🔴 ▼"

    return "🟡 ◆"


def get_diff_text(price: float, prev: float, symbol: str) -> str:
    if price <= 0 or prev <= 0:
        return "—"

    diff = price - prev
    sign = "+" if diff >= 0 else "-"

    return f"{sign}{format_price(abs(diff), symbol)}"


async def get_snapshot() -> dict:
    async with price_lock:
        return {
            symbol: data.copy()
            for symbol, data in prices.items()
        }


async def mark_displayed():
    async with price_lock:
        for symbol in prices:
            prices[symbol]["display_prev"] = prices[symbol]["price"]


def build_coin_field(symbol: str, data: dict) -> tuple[str, str]:
    price = data["price"]
    prev = data["display_prev"]
    change = data["change"]
    volume = data["volume"]

    price_text = format_price(price, symbol)
    change_text = get_change_text(change)
    status_icon = get_status_icon(change)
    diff_text = get_diff_text(price, prev, symbol)
    volume_text = format_volume(volume)

    name = f"{symbol} {status_icon}"

    value = (
        f"**Price:** `{price_text}`\n"
        f"**24h:** `{change_text}`\n"
        f"**Prev:** `{diff_text}`\n"
        f"**Vol:** `{volume_text}`"
    )

    return name, value


def build_embed(snapshot: dict) -> discord.Embed:
    now = datetime.now(timezone.utc)

    embed = discord.Embed(
        title="🚀 Crypto Live Monitor",
        color=get_market_color(snapshot),
        timestamp=now,
    )

    # First row: BTC / ETH / SOL
    for symbol in ("BTC", "ETH", "SOL"):
        name, value = build_coin_field(symbol, snapshot[symbol])
        embed.add_field(
            name=name,
            value=value,
            inline=True,
        )

    # Vertical space between rows
    embed.add_field(
        name="\u200b",
        value="\u200b\n\u200b",
        inline=False,
    )

    # Second row: BNB / XRP / ADA
    for symbol in ("BNB", "XRP", "ADA"):
        name, value = build_coin_field(symbol, snapshot[symbol])
        embed.add_field(
            name=name,
            value=value,
            inline=True,
        )

    embed.set_footer(
        text=f"Binance WebSocket • Updates every {UPDATE_INTERVAL}s"
    )

    return embed


async def binance_ws():
    streams = "/".join(
        f"{coin['stream']}@ticker"
        for coin in COINS
    )

    url = f"wss://stream.binance.com:9443/stream?streams={streams}"

    while True:
        try:
            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=10,
            ) as ws:
                print("[INFO] Connected to Binance WebSocket")

                async for raw in ws:
                    msg = json.loads(raw)

                    data = msg.get("data", {})
                    stream = msg.get("stream", "").split("@")[0]
                    symbol = STREAM_TO_SYMBOL.get(stream)

                    if not symbol or not data:
                        continue

                    new_price = float(data.get("c", 0))
                    change = float(data.get("P", 0))
                    volume = float(data.get("q", 0))

                    async with price_lock:
                        prices[symbol]["price"] = new_price
                        prices[symbol]["change"] = change
                        prices[symbol]["volume"] = volume

        except Exception as e:
            print(f"[ERROR] WebSocket error: {e} — reconnecting in 5s")
            await asyncio.sleep(5)


async def discord_updater():
    global monitor_message

    await client.wait_until_ready()

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        try:
            channel = await client.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"[ERROR] Channel {CHANNEL_ID} not found: {e}")
            return

    while not client.is_closed():
        try:
            snapshot = await get_snapshot()

            if all(data["price"] <= 0 for data in snapshot.values()):
                print("[INFO] Waiting for first Binance data...")
                await asyncio.sleep(2)
                continue

            embed = build_embed(snapshot)

            if monitor_message is None:
                monitor_message = await channel.send(embed=embed)
                print(f"[INFO] Monitor message created: {monitor_message.id}")
            else:
                await monitor_message.edit(embed=embed)
                print(f"[INFO] Updated at {datetime.now().strftime('%H:%M:%S')}")

            await mark_displayed()

        except discord.NotFound:
            print("[WARN] Monitor message was deleted. Creating a new one...")
            monitor_message = None

        except discord.HTTPException as e:
            retry_after = getattr(e, "retry_after", None)

            if retry_after:
                print(f"[WARN] Rate limited — waiting {retry_after:.1f}s")
                await asyncio.sleep(retry_after)
                continue

            print(f"[ERROR] Discord HTTP error: {e}")

        except Exception as e:
            print(f"[ERROR] Discord updater error: {e}")

        await asyncio.sleep(UPDATE_INTERVAL)


@client.event
async def on_ready():
    global tasks_started

    print(f"[INFO] Logged in as {client.user}")

    if tasks_started:
        return

    tasks_started = True

    asyncio.create_task(binance_ws())
    asyncio.create_task(discord_updater())


if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Add it to your .env file.")

if CHANNEL_ID == 0:
    raise RuntimeError("CHANNEL_ID is missing or invalid. Add it to your .env file.")


client.run(DISCORD_TOKEN)