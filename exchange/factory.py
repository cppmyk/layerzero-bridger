import os
from dotenv import load_dotenv

from exchange.binance.binance import Binance
from exchange.okex.okex import Okex

load_dotenv()


class ExchangeFactory:
    @staticmethod
    def create(exchange_name):
        if exchange_name.lower() == "binance":
            api_key = os.getenv("BINANCE_API_KEY")
            secret_key = os.getenv("BINANCE_SECRET_KEY")

            return Binance(api_key, secret_key)
        elif exchange_name.lower() == "okex":
            api_key = os.getenv("OKEX_API_KEY")
            secret_key = os.getenv("OKEX_SECRET_KEY")
            password = os.getenv("OKEX_PASSWORD")

            return Okex(api_key, secret_key, password)
        else:
            raise ValueError(f"Unknown exchange: {exchange_name}")
