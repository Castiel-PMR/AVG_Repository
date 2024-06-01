import aiohttp
import asyncio
import datetime
import logging
import configparser
import csv
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Чтение конфигурационного файла
config = configparser.ConfigParser()
config.read('config.ini')

# Ваш API ключ и секретный ключ
api_key = config['BINANCE']['API_KEY']

# Список интересующих вас монет
coins = config['BINANCE']['COINS'].split(',')

# Базовый URL для Binance API
base_url = 'https://api.binance.com/api/v3/depth'

# Ваш Telegram Bot Token и Chat ID
TELEGRAM_TOKEN = config['TELEGRAM']['TOKEN']
CHAT_ID = config['TELEGRAM']['CHAT_ID']

# Интервал опроса в секундах и продолжительность сбора данных
try:
    INTERVAL = int(config['SETTINGS']['INTERVAL'])
    DURATION = int(config['SETTINGS']['DURATION'])
except ValueError as e:
    logger.error(f"Error reading settings: {e}")
    raise

CSV_FILE = 'data.csv'

def initialize_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['timestamp', 'avg'])

def update_csv(timestamp, avg):
    with open(CSV_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, avg])

def calculate_wait_time(interval_minutes: int) -> int:
    now = datetime.datetime.now()
    total_minutes = now.hour * 60 + now.minute
    next_interval = ((total_minutes // interval_minutes) + 1) * interval_minutes
    wait_minutes = next_interval - total_minutes
    wait_seconds = wait_minutes * 60 - now.second
    return wait_seconds

async def send_telegram_message(chat_id: str, token: str, message: str):
    base_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(base_url, json=payload) as response:
            if response.status != 200:
                logger.error(f"Failed to send message: {response.status}")
            else:
                logger.info("Message sent successfully")

async def get_data_for_coin(session: aiohttp.ClientSession, coin: str):
    await asyncio.sleep(0.1)  # задержка в 100 миллисекунд перед каждым запросом
    url = f"{base_url}?symbol={coin}&limit=500"
    try:
        logger.info(f"Requesting data for {coin}")
        async with session.get(url, headers={'X-MBX-APIKEY': api_key}, timeout=10) as response:
            if response.status != 200:
                logger.error(f"Failed to retrieve data for {coin}: {response.status}")
                return 0, 0
            data = await response.json()
            if 'bids' in data and 'asks' in data:
                bid_sum = round(sum(float(order[1]) * float(order[0]) for order in data['bids']))
                ask_sum = round(sum(float(order[1]) * float(order[0]) for order in data['asks']))
                logger.info(f"Data for {coin} received: bids={bid_sum}, asks={ask_sum}")
                return bid_sum, ask_sum
            else:
                logger.error(f"Invalid data for {coin}: {data}")
                return 0, 0
    except Exception as e:
        logger.exception(f"Error retrieving data for {coin}")
        return 0, 0

async def main():
    initialize_csv()
    wait_seconds = calculate_wait_time(DURATION // 60)
    logger.info(f"Waiting {wait_seconds} seconds until the next interval")
    await asyncio.sleep(wait_seconds)

    while True:
        logger.info("Starting new data collection cycle")

        bids_15min = []
        asks_15min = []
        ratios = []

        num_iterations = DURATION // INTERVAL

        for i in range(num_iterations):  # Итерации для сбора данных в течение 15 минут
            logger.info(f"Iteration {i+1} of {num_iterations}")
            async with aiohttp.ClientSession() as session:
                results = await asyncio.gather(*(get_data_for_coin(session, coin) for coin in coins))
                for bid, ask in results:
                    bids_15min.append(bid)
                    asks_15min.append(ask)
                    ratio = bid / ask if ask != 0 else 0
                    ratios.append(ratio)
            await asyncio.sleep(INTERVAL)

        average_bid = sum(bids_15min) / num_iterations
        average_ask = sum(asks_15min) / num_iterations
        avg_ratio = sum(ratios) / len(ratios) if len(ratios) > 0 else 0
        bid_to_ask_ratio = average_bid / average_ask if average_ask != 0 else 0

        formatted_bid = f"{average_bid / 10 ** 6:.0f} млн $"
        formatted_ask = f"{average_ask / 10 ** 6:.0f} млн $"
        message = f"""ASK: {formatted_ask}
BID: {formatted_bid}
AVG: {avg_ratio:.2f}
D: {bid_to_ask_ratio:.2f}"""

        logger.info("Sending message to Telegram")
        await send_telegram_message(CHAT_ID, TELEGRAM_TOKEN, message)

        # Обновление CSV файла
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        update_csv(timestamp, avg_ratio)

        logger.info("Starting new data collection cycle immediately")

if __name__ == "__main__":
    asyncio.run(main())
