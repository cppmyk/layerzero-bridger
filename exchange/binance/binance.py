import logging
from typing import List

import ccxt

from base.errors import ExchangeError, NotWhitelistedAddress, WithdrawNotFound
from exchange.binance.constants import BinanceConstants
from exchange.exchange import Exchange, WithdrawInfo, WithdrawStatus

logger = logging.getLogger(__name__)


class Binance(Exchange):
    def __init__(self, api_key: str, secret_key: str):
        super().__init__('binance')

        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'options': {
                'defaultType': 'spot'
            }
        })

    def withdraw(self, symbol: str, amount: float, network: str, address: str) -> str:
        """ Method that initiates the withdrawal and returns the withdrawal id """

        logger.info(f'{symbol} withdraw initiated. Amount: {amount}. Network: {network}. Address: {address}')
        withdraw_info = self.get_withdraw_info(symbol, network)

        try:
            result = self.exchange.withdraw(symbol, amount, address, tag=None, params={"network": withdraw_info.chain})
        except Exception as ex:
            if 'Withdrawal address is not whitelisted for verification exemption' in str(ex):
                raise NotWhitelistedAddress(f'Unable to withdraw {symbol}({network}) to {address}. '
                                            f'The address must be added to the whitelist') from ex
            raise

        logger.debug('Withdraw result:', result)
        withdraw_id = result['id']

        return str(withdraw_id)

    def _get_withdraw_infos(self, symbol: str) -> List[WithdrawInfo]:
        currencies = self.exchange.fetch_currencies()
        chains_info = currencies[symbol]['networks']

        result = []

        for chain_info in chains_info:
            info = WithdrawInfo(symbol, chain_info['network'], float(chain_info['withdrawFee']),
                                float(chain_info['withdrawMin']))
            result.append(info)

        return result

    def get_withdraw_info(self, symbol: str, network: str) -> WithdrawInfo:
        binance_network = BinanceConstants.NETWORKS[network]
        withdraw_options = self._get_withdraw_infos(symbol)

        withdraw_info = next((option for option in withdraw_options if option.chain == binance_network), None)

        if not withdraw_info:
            raise ExchangeError(f"OKEX doesn't support {symbol}({network}) withdrawals")

        return withdraw_info

    def get_withdraw_status(self, withdrawal_id: str) -> WithdrawStatus:
        withdrawals_info = self.exchange.fetch_withdrawals()
        withdrawal_info = next((withdrawal for withdrawal in withdrawals_info if withdrawal['id'] == withdrawal_id),
                               None)

        if not withdrawal_info:
            raise WithdrawNotFound(f"Withdraw {withdrawal_id} can't be found on Binance")

        return self._parse_withdraw_status(withdrawal_info)

    def _get_min_notional(self, symbol: str) -> float:
        trading_symbol = symbol + '/USDT'
        markets = self.exchange.load_markets()

        market = markets[trading_symbol]
        minimal_notional = market['info']['filters'][6]['minNotional']

        return float(minimal_notional)

    def _get_precision(self, symbol: str) -> int:
        currencies = self.exchange.fetch_currencies()
        currency_info = currencies[symbol]
        decimals = int(currency_info['precision'])

        return decimals

    def buy_tokens_with_usdt(self, symbol: str, amount: float) -> float:
        logger.info(f'{symbol} purchase initiated. Amount: {amount}')
        trading_symbol = symbol + '/USDT'

        ticker = self.exchange.fetch_ticker(trading_symbol)
        price = ticker['last']

        notional = amount * price
        min_notional = self._get_min_notional(symbol)
        while notional < min_notional:
            amount *= 1.05
            notional = amount * price

        price *= 1.05  # 5% more to perform market buy

        creation_result = self.exchange.create_limit_buy_order(trading_symbol, amount, price)

        filled = float(creation_result['filled'])
        fee_rate = 0.001
        fee = filled * fee_rate
        received_amount = filled - fee

        return received_amount

    def get_funding_balance(self, symbol: str) -> float:
        balance = self.exchange.fetch_balance()

        if symbol not in balance:
            return 0
        token_balance = float(balance[symbol]['free'])

        return token_balance

    def buy_token_and_withdraw(self, symbol: str, amount: float, network: str, address: str) -> None:
        withdraw_info = self.get_withdraw_info(symbol, network)

        if withdraw_info.min_amount > amount:
            amount = withdraw_info.min_amount
        amount += withdraw_info.fee * 3

        balance = self.get_funding_balance(symbol)
        if balance < amount:
            # Multiplying to avoid decimals casting
            amount_to_withdraw = self.buy_tokens_with_usdt(symbol, amount) * 0.99
        else:
            amount_to_withdraw = amount

        decimals = self._get_precision(symbol)
        rounded_amount = round(amount_to_withdraw, decimals)

        withdraw_id = self.withdraw(symbol, rounded_amount, network, address)
        self.wait_for_withdraw_to_finish(withdraw_id)
