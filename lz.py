import argparse
import logging
import random
import sys
import time
from typing import Any

from base.errors import NotWhitelistedAddress
from logic import AccountThread
from config import ConfigurationHelper, DEFAULT_PRIVATE_KEYS_FILE_PATH, BridgerMode, RefuelMode
from logger import setup_logger
from exchange import ExchangeFactory

from utility import WalletHelper

logger = logging.getLogger(__name__)


class LayerZeroBridger:

    def __init__(self) -> None:
        setup_logger()
        self.wh = WalletHelper()

    def main(self) -> None:
        parser = argparse.ArgumentParser(description="layerzero-bridger CLI")
        subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        self._create_generate_parser(subparsers)
        self._create_withdraw_parser(subparsers)
        self._create_run_bridger_parser(subparsers)

        args = parser.parse_args()
        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()

    def generate_private_keys(self, args: argparse.Namespace) -> None:
        if args.num_keys <= 0:
            logger.info("Number of keys must be a positive integer")
            sys.exit(1)

        filename = args.filename if args.filename else ""
        private_keys = []

        for _ in range(args.num_keys):
            pk = self.wh.generate_private_key()
            private_keys.append(pk)

        self.wh.to_txt(private_keys, filename)

    def withdraw_funds(self, args: argparse.Namespace) -> None:
        token = args.token.upper()
        network = args.network

        private_keys = self.wh.load_private_keys(args.private_keys)
        addresses = self.wh.resolve_addresses(private_keys)

        if not addresses:
            logger.info('You should specify at least 1 address for the withdrawal')
            sys.exit(1)

        exchange = ExchangeFactory.create(args.exchange)

        if not exchange.is_withdraw_supported(token, network):
            logger.info(f'{token} withdrawal on the {network} network is not available')
            sys.exit(1)

        for idx, address in enumerate(addresses):
            logger.info(f'Processing {idx}/{len(addresses)}')

            amount = random.uniform(args.min_amount, args.max_amount)
            decimals = random.randint(3, 6)  # May be improved
            amount = round(amount, decimals)

            try:
                exchange.withdraw(token, amount, network, address)
            except NotWhitelistedAddress as ex:
                logger.info(str(ex))
                sys.exit(1)

            if idx == len(addresses) - 1:
                logger.info('All withdrawals are successfully completed')
                sys.exit(0)

            waiting_time = random.uniform(args.min_time, args.max_time)
            logger.info(f'Waiting {round(waiting_time, 1)} minutes before the next withdrawal')
            time.sleep(waiting_time * 60)  # Convert waiting time to seconds

    def run_bridger(self, args: argparse.Namespace) -> None:
        config = ConfigurationHelper()
        config.check_configuration()

        bridger_mode = BridgerMode(args.bridger_mode)
        refuel_mode = RefuelMode(args.refuel_mode)
        bridges_limit = args.limit

        private_keys = self.wh.load_private_keys(args.private_keys)

        if not private_keys:
            logger.info("Zero private keys was loaded")
            sys.exit(1)

        accounts = []

        for account_id, private_key in enumerate(private_keys):
            accounts.append(AccountThread(account_id, private_key, bridger_mode, refuel_mode, bridges_limit))
            accounts[account_id].start()

        for account in accounts:
            account.join()

    def _create_generate_parser(self, subparsers: Any) -> None:
        generate_parser = subparsers.add_parser("generate", help="Generate new private keys")

        generate_parser.add_argument("num_keys", type=int, help="Number of private keys to generate")
        generate_parser.add_argument("filename", nargs="?", help="Path to the file to save the private keys")

        generate_parser.set_defaults(func=self.generate_private_keys)

    def _create_withdraw_parser(self, subparsers: Any) -> None:
        withdraw_parser = subparsers.add_parser("withdraw", help="Withdraw funds from exchange to account addresses")

        withdraw_parser.add_argument("token", help="Token to be withdrawn")
        withdraw_parser.add_argument("network", choices=["Arbitrum", "Ethereum", "Optimism", "Polygon",
                                                         "Fantom", "Avalanche", "BSC"],
                                     help="Network for the withdrawal")

        # Amount
        withdraw_parser.add_argument("min_amount", type=float, help="Minimum amount of withdrawal")
        withdraw_parser.add_argument("max_amount", type=float, help="Maximum amount of withdrawal")

        # Waiting time
        withdraw_parser.add_argument("--min_time", type=float, default=0, dest="min_time",
                                     help="Minimum waiting time between withdraws in minutes")
        withdraw_parser.add_argument("--max_time", type=float, default=0, dest="max_time",
                                     help="Maximum waiting time between withdraws in minutes")

        withdraw_parser.add_argument("--keys", type=str, default=DEFAULT_PRIVATE_KEYS_FILE_PATH,
                                     dest="private_keys",
                                     help="Path to the file containing private keys of the account addresses")
        withdraw_parser.add_argument("--exchange", choices=["binance", "okex"], default="binance", dest='exchange',
                                     help="Exchange name (binance, okex)")

        withdraw_parser.set_defaults(func=self.withdraw_funds)

    def _create_run_bridger_parser(self, subparsers: Any) -> None:
        run_parser = subparsers.add_parser("run", help="Run the LayerZero bridger")
        run_parser.add_argument("bridger_mode", choices=["stargate", "btcb"],
                                help="Running mode (stargate, btcb)")
        run_parser.add_argument("--keys", type=str, default=DEFAULT_PRIVATE_KEYS_FILE_PATH, dest="private_keys",
                                help="Path to the file containing private keys")
        run_parser.add_argument("--refuel", choices=["manual", "binance", "okex"], default="manual", dest='refuel_mode',
                                help="Refuel mode (manual, binance, okex)")
        run_parser.add_argument("--limit", type=int, help="Maximum number of bridges to be executed")

        run_parser.set_defaults(func=self.run_bridger)


if __name__ == "__main__":
    app = LayerZeroBridger()
    app.main()
