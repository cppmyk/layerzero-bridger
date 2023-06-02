from base.errors import StablecoinNotSupportedByChain
from network.network import EVMNetwork
from utility import Stablecoin


class BalanceHelper:
    def __init__(self, network: EVMNetwork, address: str):
        self.network = network
        self.address = address

    def get_native_token_balance(self) -> int:
        return self.network.get_balance(self.address)

    def get_stablecoin_balance(self, stablecoin: Stablecoin) -> int:
        if stablecoin.symbol not in self.network.supported_stablecoins:
            raise StablecoinNotSupportedByChain(f"{stablecoin.symbol} is not supported by {self.network.name}")

        return self.network.get_token_balance(stablecoin.contract_address, self.address)
