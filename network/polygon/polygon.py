import logging
import random

from network.network import EVMNetwork
from network.polygon.constants import PolygonConstants
from stargate import StargateConstants
from utility import Stablecoin

logger = logging.getLogger(__name__)


class Polygon(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDT': Stablecoin('USDT', PolygonConstants.USDT_CONTRACT_ADDRESS, PolygonConstants.USDC_DECIMALS,
                               PolygonConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDT']),
            'USDC': Stablecoin('USDC', PolygonConstants.USDC_CONTRACT_ADDRESS, PolygonConstants.USDC_DECIMALS,
                               PolygonConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(PolygonConstants.NAME, PolygonConstants.NATIVE_TOKEN, PolygonConstants.RPC,
                         PolygonConstants.LAYERZERO_CHAIN_ID, PolygonConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def get_approve_gas_limit(self) -> int:
        return PolygonConstants.APPROVE_GAS_LIMIT

    def get_max_fee_per_gas(self) -> int:
        return int(self.get_current_gas() * 2.5)

    def get_transaction_gas_params(self) -> dict:
        max_priority_fee = int(self.w3.eth.max_priority_fee * random.uniform(1, 2))

        gas_params = {
            'maxFeePerGas': self.get_max_fee_per_gas(),
            'maxPriorityFeePerGas': max_priority_fee
        }

        logger.debug(f"{self.name} gas params fetched. Params: {gas_params}")

        return gas_params
