import argparse
import time

from logic import AccountThread
from config import ConfigurationHelper
from logger import setup_logger
from eth_account import Account


class LayerZeroApp:

    def main(self) -> None:
        parser = argparse.ArgumentParser(description="LayerZero Application CLI")
        subparsers = parser.add_subparsers(title="subcommands", dest="subcommand")

        # Create subparser for the "generate" command
        generate_parser = subparsers.add_parser("generate", help="Generate new private keys")
        generate_parser.add_argument("num_keys", type=int, help="Number of private keys to generate")
        generate_parser.set_defaults(func=self.generate_private_keys)

        # Create subparser for the "run" command
        run_parser = subparsers.add_parser("run", help="Run the layerzero-bridger")
        run_parser.set_defaults(func=self.run)

        args = parser.parse_args()
        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()

    @staticmethod
    def generate_private_keys(args: argparse.Namespace) -> None:
        print(f"{'-' * 27} Generated {'-' * 28}")
        for _ in range(args.num_keys):
            print(Account.create().key.hex())
        print(f"{'-' * 27} /Generated {'-' * 27}")

    @staticmethod
    def run(args: argparse.Namespace) -> None:
        setup_logger()

        config = ConfigurationHelper()
        config.check_configuration()

        accounts = []

        for account_id, private_key in enumerate(config.load_default_keys()):
            accounts.append(AccountThread(account_id, private_key))
            accounts[account_id].start()

        for account in accounts:
            account.join()


if __name__ == "__main__":
    app = LayerZeroApp()
    app.main()
