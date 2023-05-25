from network import EVMNetwork, Stablecoin
from base.errors import StablecoinNotSupportedByChain


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

    def is_enough_native_token_balance_for_stargate_swap_fee(self, dst_network: EVMNetwork):
        account_balance = self.get_native_token_balance()
        gas_price = self.network.estimate_swap_gas_price()
        layerzero_fee = self.network.estimate_layerzero_swap_fee(dst_network.stargate_chain_id,
                                                                 self.address)

        enough_native_token_balance = account_balance > (gas_price + layerzero_fee)

        return enough_native_token_balance
