import logging
from typing import List

import ccxt

from base.errors import ExchangeError, NotWhitelistedAddress
from exchange.exchange import Exchange, WithdrawInfo, WithdrawStatus
from exchange.okex.constants import OkexConstants

logger = logging.getLogger(__name__)


class Okex(Exchange):
    def __init__(self, api_key: str, secret_key: str, api_password: str):
        ccxt_args = {'password': api_password}
        super().__init__('okex', api_key, secret_key, ccxt_args)

        self.funding_account = 'funding'
        self.trading_account = 'spot'

    def _get_withdraw_infos(self, symbol: str) -> List[WithdrawInfo]:
        currencies = self._ccxt_exc.fetch_currencies()
        chains_info = currencies[symbol]['networks']

        result = []

        for chain_info in chains_info.values():
            info = WithdrawInfo(symbol, chain_info['info']['chain'], chain_info['fee'],
                                chain_info['limits']['withdraw']['min'])
            result.append(info)

        return result

    def is_withdraw_supported(self, symbol: str, network: str) -> bool:
        if symbol in OkexConstants.TOKENS and network in OkexConstants.TOKENS[symbol]:
            return True
        return False

    def get_withdraw_info(self, symbol: str, network: str) -> WithdrawInfo:
        okx_network = OkexConstants.NETWORKS[network]
        withdraw_options = self._get_withdraw_infos(symbol)

        chain = f"{symbol}-{okx_network}"

        withdraw_info = next((option for option in withdraw_options if option.chain == chain), None)

        if not withdraw_info:
            raise ExchangeError(f"OKEX doesn't support {symbol}({network}) withdrawals")

        return withdraw_info

    def withdraw(self, symbol: str, amount: float, network: str, address: str) -> str:
        """ Method that initiates the withdrawal and returns the withdrawal id """

        logger.info(f'{symbol} withdraw initiated. Amount: {amount}. Network: {network}. Address: {address}')
        withdraw_info = self.get_withdraw_info(symbol, network)
        amount -= withdraw_info.fee
        logger.info(f'Amount with fee: {amount}')

        try:
            result = self._ccxt_exc.withdraw(symbol, amount, address,
                                             {"chain": withdraw_info.chain, 'fee': withdraw_info.fee, 'pwd': "-"})
        except Exception as ex:
            if 'Withdrawal address is not whitelisted for verification exemption' in str(ex):
                raise NotWhitelistedAddress(f'Unable to withdraw {symbol}({network}) to {address}. '
                                            f'The address must be added to the whitelist') from ex
            raise

        logger.debug(f'Withdraw result: {result}')
        withdraw_id = result['id']

        return str(withdraw_id)

    def get_withdraw_status(self, withdraw_id: str) -> WithdrawStatus:
        withdraw_info = self._ccxt_exc.fetch_withdrawal(withdraw_id)

        return self._parse_withdraw_status(withdraw_info)

    def transfer_funds(self, symbol: str, amount: float, from_account: str, to_account: str):
        logger.info(f'{symbol} transfer initiated. From {from_account} to {to_account}')
        result = self._ccxt_exc.transfer(symbol, amount, from_account, to_account)
        logger.debug('Transfer result:', result)

    def buy_tokens_with_usdt(self, symbol: str, amount: float) -> float:
        logger.info(f'{symbol} purchase initiated. Amount: {amount}')
        trading_symbol = symbol + '/USDT'

        creation_result = self._ccxt_exc.create_market_order(trading_symbol, 'buy', amount)
        order = self._ccxt_exc.fetch_order(creation_result['id'], trading_symbol)

        filled = float(order['filled'])
        fee = float(order['fee']['cost'])
        received_amount = filled - fee

        return received_amount

    def get_funding_balance(self, symbol: str) -> float:
        balance = self._ccxt_exc.fetch_balance(params={'type': self.funding_account})

        if symbol not in balance['total']:
            return 0
        token_balance = float(balance['total'][symbol])

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
            self.transfer_funds(symbol, amount_to_withdraw, self.trading_account, self.funding_account)
        else:
            amount_to_withdraw = amount

        withdraw_id = self.withdraw(symbol, amount_to_withdraw, network, address)
        self.wait_for_withdraw_to_finish(withdraw_id)
