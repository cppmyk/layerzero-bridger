import logging
from dataclasses import dataclass
from typing import List

import ccxt

from base.errors import ExchangeError, NotWhitelistedAddress
from refuel.constants import OkexConstants

logger = logging.getLogger(__name__)


@dataclass
class WithdrawInfo:
    symbol: str
    chain: str
    fee: float
    min_amount: float


class Okex:
    def __init__(self, api_key: str, secret_key: str, api_password: str):
        self.exchange = ccxt.okex({
            'apiKey': api_key,
            'secret': secret_key,
            'password': api_password,
        })
        self.funding_account = 'funding'
        self.trading_account = 'spot'

    def _get_withdraw_infos(self, symbol: str) -> List[WithdrawInfo]:
        currencies = self.exchange.fetch_currencies()
        chains_info = currencies[symbol]['networks']

        result = []

        for chain_info in chains_info.values():
            info = WithdrawInfo(symbol, chain_info['info']['chain'], chain_info['fee'],
                                chain_info['limits']['withdraw']['min'])
            result.append(info)

        return result

    def get_withdraw_info(self, symbol: str, network: str):
        okx_network = OkexConstants.NETWORKS[network]
        withdraw_options = self._get_withdraw_infos(symbol)

        chain = f"{symbol}-{okx_network}"

        withdraw_info = next((option for option in withdraw_options if option.chain == chain), None)

        if not withdraw_info:
            raise ExchangeError(f"OKEX doesn't support {symbol}({network}) withdrawals")

        return withdraw_info

    def withdraw(self, symbol: str, amount: float, network: str, address: str):
        logger.info(f'{symbol} withdraw initiated. Amount: {amount}. Network: {network}. Address: {address}')
        withdraw_info = self.get_withdraw_info(symbol, network)
        amount -= withdraw_info.fee
        logger.info(f'Amount with fee: {amount}')

        try:
            result = self.exchange.withdraw(symbol, amount, address,
                                            {"chain": withdraw_info.chain, 'fee': withdraw_info.fee, 'pwd': "-"})
        except Exception as ex:
            if 'Withdrawal address is not whitelisted for verification exemption' in str(ex):
                raise NotWhitelistedAddress(f'Unable to withdraw {symbol}({network}) to {address}. '
                                            f'The address must be added to the whitelist') from ex
            raise

        logger.debug('Withdraw result:', result)

    def transfer_funds(self, symbol: str, amount: float, from_account: str, to_account: str):
        logger.info(f'{symbol} transfer initiated. From {from_account} to {to_account}')
        result = self.exchange.transfer(symbol, amount, from_account, to_account)
        logger.debug('Transfer result:', result)

    def buy_tokens_with_usdt(self, symbol: str, amount: float) -> float:
        logger.info(f'{symbol} purchase initiated. Amount: {amount}')
        trading_symbol = symbol + '/USDT'

        creation_result = self.exchange.create_market_order(trading_symbol, 'buy', amount)
        order = self.exchange.fetch_order(creation_result['id'], trading_symbol)

        filled = float(order['filled'])
        fee = float(order['fee']['cost'])
        received_amount = filled - fee

        return received_amount

    def get_funding_balance(self, symbol: str) -> float:
        balance = self.exchange.fetch_balance(params={'type': 'funding'})

        if symbol not in balance['total']:
            return 0
        token_balance = float(balance['total'][symbol])

        return token_balance

    def buy_token_and_withdraw(self, symbol: str, amount: float, network: str, address: str):
        withdraw_info = self.get_withdraw_info(symbol, network)

        if withdraw_info.min_amount > amount:
            amount = withdraw_info.min_amount
        amount += withdraw_info.fee * 3

        bought_amount = self.buy_tokens_with_usdt(symbol, amount) * 0.99  # Multiplying to avoid decimals casting

        self.transfer_funds(symbol, bought_amount, self.trading_account, self.funding_account)
        self.withdraw(symbol, bought_amount, network, address)
