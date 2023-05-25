from network import EVMNetwork
from network.stablecoin import Stablecoin
from network.arbitrum.constants import ArbitrumConstants
from stargate import StargateConstants


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

    def _get_approve_gas_limit(self) -> int:
        return ArbitrumConstants.APPROVE_GAS_LIMIT
