from network.network import EVMNetwork
from network.optimism.constants import OptimismConstants
from stargate import StargateConstants
from utility import Stablecoin


class Optimism(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDC': Stablecoin('USDC', OptimismConstants.USDC_CONTRACT_ADDRESS, OptimismConstants.USDC_DECIMALS,
                               OptimismConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(OptimismConstants.NAME, OptimismConstants.NATIVE_TOKEN, OptimismConstants.RPC,
                         OptimismConstants.STARGATE_CHAIN_ID, OptimismConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def get_approve_gas_limit(self) -> int:
        return OptimismConstants.APPROVE_GAS_LIMIT

    def get_transaction_gas_params(self) -> dict:
        gas_params = {
            'gasPrice': self.get_current_gas()
        }

        return gas_params
