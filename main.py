import argparse
import random
import sys
import time
from typing import Any

from base.errors import NotWhitelistedAddress
from logic import AccountThread
from config import ConfigurationHelper, DEFAULT_PRIVATE_KEYS_FILE_PATH, BridgerMode
from logger import setup_logger
from exchange import ExchangeFactory

from utility import WalletHelper


class LayerZeroApp:

    def __init__(self) -> None:
        setup_logger()
        self.wh = WalletHelper()

    def generate_private_keys(self, args: argparse.Namespace) -> None:
        if args.num_keys <= 0:
            print("Number of keys must be a positive integer")
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
            print('You should specify at least 1 address for the withdrawal')
            sys.exit(1)

        exchange = ExchangeFactory.create(args.exchange)

        if not exchange.is_withdraw_supported(token, network):
            print(f'{token} withdrawal on the {network} network is not available')
            sys.exit(1)

        for address in addresses:
            amount = random.uniform(args.min_amount, args.max_amount)
            decimals = random.randint(4, 7)  # May be improved
            amount = round(amount, decimals)

            try:
                exchange.withdraw(token, amount, network, address)
            except NotWhitelistedAddress as ex:
                print(str(ex))
                exit(1)

            waiting_time = random.uniform(args.min_time, args.max_time)
            time.sleep(waiting_time * 60)  # Convert waiting time to seconds

    def run_bridger(self, args: argparse.Namespace) -> None:
        config = ConfigurationHelper()
        config.check_configuration()

        mode = BridgerMode(args.mode)
        accounts = []

        for account_id, private_key in enumerate(self.wh.load_private_keys(args.private_keys)):
            accounts.append(AccountThread(account_id, private_key, mode))
            accounts[account_id].start()

        for account in accounts:
            account.join()

    def create_generate_parser(self, subparsers: Any) -> None:
        generate_parser = subparsers.add_parser("generate", help="Generate new private keys")

        generate_parser.add_argument("num_keys", type=int, help="Number of private keys to generate")
        generate_parser.add_argument("filename", nargs="?", help="Path to the file to save the private keys")

        generate_parser.set_defaults(func=self.generate_private_keys)

    def create_withdraw_parser(self, subparsers: Any) -> None:
        withdraw_parser = subparsers.add_parser("withdraw", help="Withdraw funds from exchange to account addresses")

        withdraw_parser.add_argument("token", help="Token to be withdrawn")
        withdraw_parser.add_argument("network", help="Network for the withdrawal")

        # Amount
        withdraw_parser.add_argument("--min-amount", type=float, dest="min_amount",
                                     help="Minimum amount of withdrawal", required=True)
        withdraw_parser.add_argument("--max-amount", type=float, dest="max_amount",
                                     help="Maximum amount of withdrawal", required=True)

        # Waiting time
        withdraw_parser.add_argument("--min-waiting-time", type=float, default=0, dest="min_time",
                                     help="Minimum waiting time between withdraws in minutes")
        withdraw_parser.add_argument("--max-waiting-time", type=float, default=0, dest="max_time",
                                     help="Maximum waiting time between withdraws in minutes")

        withdraw_parser.add_argument("--private-keys", type=str, default=DEFAULT_PRIVATE_KEYS_FILE_PATH,
                                     dest="private_keys",
                                     help="Path to the file containing private keys of the account addresses")
        withdraw_parser.add_argument("--exchange", choices=["binance", "okex"], default="binance", dest='exchange',
                                     help="Exchange name (binance, okex)")

        withdraw_parser.set_defaults(func=self.withdraw_funds)

    def create_run_bridger_parser(self, subparsers: Any) -> None:
        run_parser = subparsers.add_parser("run", help="Run the LayerZero bridger")
        run_parser.add_argument("mode", choices=["stargate", "btcb", "testnet"],
                                help="Running mode (stargate, btcb, testnet)")
        run_parser.add_argument("--private-keys", type=str, default=DEFAULT_PRIVATE_KEYS_FILE_PATH, dest="private_keys",
                                help="Path to the file containing private keys")
        run_parser.set_defaults(func=self.run_bridger)

    def main(self) -> None:
        parser = argparse.ArgumentParser(description="LayerZeroApp CLI")
        subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        self.create_generate_parser(subparsers)
        self.create_withdraw_parser(subparsers)
        self.create_run_bridger_parser(subparsers)

        args = parser.parse_args()
        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()


if __name__ == "__main__":
    app = LayerZeroApp()
    app.main()
