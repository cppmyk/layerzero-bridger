import logging

from network.arbitrum.constants import ArbitrumConstants
from network.network import EVMNetwork
from stargate import StargateConstants
from utility import Stablecoin

logger = logging.getLogger(__name__)


class Arbitrum(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDT': Stablecoin('USDT', ArbitrumConstants.USDT_CONTRACT_ADDRESS, ArbitrumConstants.USDT_DECIMALS,
                               ArbitrumConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDT']),
            'USDC': Stablecoin('USDC', ArbitrumConstants.USDC_CONTRACT_ADDRESS, ArbitrumConstants.USDC_DECIMALS,
                               ArbitrumConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(ArbitrumConstants.NAME, ArbitrumConstants.NATIVE_TOKEN, ArbitrumConstants.RPC,
                         ArbitrumConstants.LAYERZERO_CHAIN_ID, ArbitrumConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def get_approve_gas_limit(self) -> int:
        return ArbitrumConstants.APPROVE_GAS_LIMIT

    def get_max_fee_per_gas(self) -> int:
        # Fixed value
        return 135000000

    def get_transaction_gas_params(self) -> dict:
        gas_params = {
            'maxFeePerGas': self.get_max_fee_per_gas(),
            'maxPriorityFeePerGas': 0
        }

        logger.debug(f"{self.name} gas params fetched. Params: {gas_params}")

        return gas_params
