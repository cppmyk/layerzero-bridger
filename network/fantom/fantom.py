from network.fantom.constants import FantomConstants
from network.network import EVMNetwork
from stargate import StargateConstants
from utility import Stablecoin


class Fantom(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDC': Stablecoin('USDC', FantomConstants.USDC_CONTRACT_ADDRESS, FantomConstants.USDC_DECIMALS,
                               FantomConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(FantomConstants.NAME, FantomConstants.NATIVE_TOKEN, FantomConstants.RPC,
                         FantomConstants.LAYERZERO_CHAIN_ID, FantomConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def get_approve_gas_limit(self) -> int:
        return FantomConstants.APPROVE_GAS_LIMIT

    def get_transaction_gas_params(self) -> dict:
        gas_params = {
            'gasPrice': self.get_current_gas()
        }

        return gas_params
