import logging
import random

from network.avalanche.constants import AvalancheConstants
from network.network import EVMNetwork
from stargate import StargateConstants
from utility import Stablecoin

logger = logging.getLogger(__name__)


class Avalanche(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDT': Stablecoin('USDT', AvalancheConstants.USDT_CONTRACT_ADDRESS, AvalancheConstants.USDT_DECIMALS,
                               AvalancheConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDT']),
            'USDC': Stablecoin('USDC', AvalancheConstants.USDC_CONTRACT_ADDRESS, AvalancheConstants.USDC_DECIMALS,
                               AvalancheConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(AvalancheConstants.NAME, AvalancheConstants.NATIVE_TOKEN, AvalancheConstants.RPC,
                         AvalancheConstants.LAYERZERO_CHAIN_ID, AvalancheConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def get_approve_gas_limit(self) -> int:
        return AvalancheConstants.APPROVE_GAS_LIMIT

    def get_max_fee_per_gas(self) -> int:
        return int(self.get_current_gas() * 1.5)

    def get_transaction_gas_params(self) -> dict:
        max_fee_per_gas = self.get_max_fee_per_gas()
        mul = random.uniform(0.9, 1)
        max_fee_per_gas = int(max_fee_per_gas * mul)

        gas_params = {
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': 1500000000
        }

        logger.debug(f"{self.name} gas params fetched. Params: {gas_params}")

        return gas_params
