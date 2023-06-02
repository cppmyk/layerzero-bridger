from network.network import EVMNetwork
from network.ethereum.constants import EthereumConstants
from utility import Stablecoin
from stargate import StargateConstants


class Ethereum(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDT': Stablecoin('USDT', EthereumConstants.USDT_CONTRACT_ADDRESS, EthereumConstants.USDT_DECIMALS,
                               EthereumConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDT']),
            'USDC': Stablecoin('USDC', EthereumConstants.USDC_CONTRACT_ADDRESS, EthereumConstants.USDC_DECIMALS,
                               EthereumConstants.STARGATE_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(EthereumConstants.NAME, EthereumConstants.NATIVE_TOKEN, EthereumConstants.RPC,
                         EthereumConstants.STARGATE_CHAIN_ID, EthereumConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def _get_approve_gas_limit(self) -> int:
        return EthereumConstants.APPROVE_GAS_LIMIT
