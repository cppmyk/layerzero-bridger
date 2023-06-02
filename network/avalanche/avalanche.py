from network.avalanche.constants import AvalancheConstants
from network.network import EVMNetwork
from stargate import StargateConstants
from utility import Stablecoin


class Avalanche(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDT': Stablecoin('USDT', AvalancheConstants.USDT_CONTRACT_ADDRESS, AvalancheConstants.USDT_DECIMALS,
                               AvalancheConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDT']),
            'USDC': Stablecoin('USDC', AvalancheConstants.USDC_CONTRACT_ADDRESS, AvalancheConstants.USDC_DECIMALS,
                               AvalancheConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(AvalancheConstants.NAME, AvalancheConstants.NATIVE_TOKEN, AvalancheConstants.RPC,
                         AvalancheConstants.STARGATE_CHAIN_ID, AvalancheConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def get_approve_gas_limit(self) -> int:
        return AvalancheConstants.APPROVE_GAS_LIMIT

    def get_transaction_gas_params(self) -> dict:
        gas_params = {
            'maxFeePerGas': int(self.get_current_gas() * 1.7),
            'maxPriorityFeePerGas': 1500000000
        }

        return gas_params
