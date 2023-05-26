from network.network import EVMNetwork
from network.optimism.constants import OptimismConstants
from network.stablecoin import Stablecoin
from stargate import StargateConstants


class Optimism(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDC': Stablecoin('USDC', OptimismConstants.USDC_CONTRACT_ADDRESS, OptimismConstants.USDC_DECIMALS,
                               OptimismConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(OptimismConstants.NAME, OptimismConstants.NATIVE_TOKEN, OptimismConstants.RPC,
                         OptimismConstants.STARGATE_CHAIN_ID, OptimismConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def _get_approve_gas_limit(self) -> int:
        return OptimismConstants.APPROVE_GAS_LIMIT
