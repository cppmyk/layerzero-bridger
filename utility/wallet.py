import os
from datetime import datetime
from typing import List

from eth_account import Account


class WalletHelper:

    def generate_private_key(self) -> str:
        account = Account.create()

        return account.key.hex()[2:]

    def resolve_address(self, private_key: str) -> str:
        account = Account.from_key(private_key)

        return account.address

    def resolve_addresses(self, private_keys: List[str]) -> List[str]:
        addresses = []
        for key in private_keys:
            addresses.append(self.resolve_address(key))

        return addresses

    def load_private_keys(self, file_path: str) -> List[str]:
        with open(file_path, 'r') as file:
            keys = file.read().splitlines()
            filtered = [s for s in keys if s]
            return filtered

    def _prepare_keys_directory(self) -> str:
        keys_dir = 'generated_keys'

        if not os.path.exists(keys_dir):
            os.makedirs(keys_dir)

        return keys_dir

    def to_txt(self, private_keys: List[str], filename: str = "") -> None:
        if not filename:
            keys_dir = self._prepare_keys_directory()
            current_date = datetime.now().strftime('%Y-%m-%d')
            current_time = datetime.now().strftime('%H-%M-%S')
            filename = f"{keys_dir}/private_keys_{current_date}_{current_time}.txt"

        with open(filename, 'a') as file:
            for key in private_keys:
                file.write(key + "\n")
