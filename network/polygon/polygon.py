from network import EVMNetwork
from network.stablecoin import Stablecoin
from network.polygon.constants import PolygonConstants
from stargate import StargateConstants


class Polygon(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDT': Stablecoin('USDT', PolygonConstants.USDT_CONTRACT_ADDRESS, PolygonConstants.USDC_DECIMALS,
                               PolygonConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDT']),
            'USDC': Stablecoin('USDC', PolygonConstants.USDC_CONTRACT_ADDRESS, PolygonConstants.USDC_DECIMALS,
                               PolygonConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(PolygonConstants.NAME, PolygonConstants.NATIVE_TOKEN, PolygonConstants.RPC,
                         PolygonConstants.STARGATE_CHAIN_ID, PolygonConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def _get_approve_gas_limit(self) -> int:
        return PolygonConstants.APPROVE_GAS_LIMIT
