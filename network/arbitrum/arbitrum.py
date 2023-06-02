from network.arbitrum.constants import ArbitrumConstants
from network.network import EVMNetwork
from stargate import StargateConstants
from utility import Stablecoin


class Arbitrum(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDT': Stablecoin('USDT', ArbitrumConstants.USDT_CONTRACT_ADDRESS, ArbitrumConstants.USDT_DECIMALS,
                               ArbitrumConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDT']),
            'USDC': Stablecoin('USDC', ArbitrumConstants.USDC_CONTRACT_ADDRESS, ArbitrumConstants.USDC_DECIMALS,
                               ArbitrumConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(ArbitrumConstants.NAME, ArbitrumConstants.NATIVE_TOKEN, ArbitrumConstants.RPC,
                         ArbitrumConstants.STARGATE_CHAIN_ID, ArbitrumConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def get_approve_gas_limit(self) -> int:
        return ArbitrumConstants.APPROVE_GAS_LIMIT

    def get_transaction_gas_params(self) -> dict:
        gas_params = {
            'maxFeePerGas': self.get_current_gas() + 35000000,
            'maxPriorityFeePerGas': 0
        }

        return gas_params
