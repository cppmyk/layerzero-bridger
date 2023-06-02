from network.ethereum.constants import EthereumConstants
from network.network import EVMNetwork
from stargate import StargateConstants
from utility import Stablecoin


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

    def get_approve_gas_limit(self) -> int:
        return EthereumConstants.APPROVE_GAS_LIMIT

    def get_transaction_gas_params(self) -> dict:
        gas_params = {
            'maxFeePerGas': int(self.get_current_gas() * 1.3),
            'maxPriorityFeePerGas': self.w3.eth.max_priority_fee * 2
        }

        return gas_params
