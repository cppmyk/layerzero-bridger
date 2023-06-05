import logging
import random

from network.ethereum.constants import EthereumConstants
from network.network import EVMNetwork
from stargate import StargateConstants
from utility import Stablecoin

logger = logging.getLogger(__name__)


class Ethereum(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDT': Stablecoin('USDT', EthereumConstants.USDT_CONTRACT_ADDRESS, EthereumConstants.USDT_DECIMALS,
                               EthereumConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDT']),
            'USDC': Stablecoin('USDC', EthereumConstants.USDC_CONTRACT_ADDRESS, EthereumConstants.USDC_DECIMALS,
                               EthereumConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(EthereumConstants.NAME, EthereumConstants.NATIVE_TOKEN, EthereumConstants.RPC,
                         EthereumConstants.LAYERZERO_CHAIN_ID, EthereumConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def get_approve_gas_limit(self) -> int:
        return EthereumConstants.APPROVE_GAS_LIMIT

    def get_max_fee_per_gas(self) -> int:
        return int(self.get_current_gas() * 1.2)

    def get_transaction_gas_params(self) -> dict:
        max_priority_fee = int(self.w3.eth.max_priority_fee * random.uniform(2, 3))

        gas_params = {
            'maxFeePerGas': self.get_max_fee_per_gas(),
            'maxPriorityFeePerGas': max_priority_fee
        }

        logger.debug(f"{self.name} gas params fetched. Params: {gas_params}")

        return gas_params
