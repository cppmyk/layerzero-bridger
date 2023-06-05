import logging

from web3.types import TxParams

from network.network import EVMNetwork
from network.optimism.constants import OptimismConstants
from stargate import StargateConstants
from utility import Stablecoin
from abi import OPTIMISM_GAS_ORACLE_ABI

logger = logging.getLogger(__name__)


class Optimism(EVMNetwork):

    def __init__(self):
        supported_stablecoins = {
            'USDC': Stablecoin('USDC', OptimismConstants.USDC_CONTRACT_ADDRESS, OptimismConstants.USDC_DECIMALS,
                               OptimismConstants.LAYERZERO_CHAIN_ID, StargateConstants.POOLS['USDC'])
        }

        super().__init__(OptimismConstants.NAME, OptimismConstants.NATIVE_TOKEN, OptimismConstants.RPC,
                         OptimismConstants.LAYERZERO_CHAIN_ID, OptimismConstants.STARGATE_ROUTER_CONTRACT_ADDRESS,
                         supported_stablecoins)

    def get_approve_gas_limit(self) -> int:
        return OptimismConstants.APPROVE_GAS_LIMIT

    def get_transaction_gas_params(self) -> dict:
        gas_params = {
            'gasPrice': self.get_current_gas()
        }

        logger.debug(f"{self.name} gas params fetched. Params: {gas_params}")

        return gas_params

    def get_l1_fee(self, tx_params: TxParams) -> int:
        oracle = self.w3.eth.contract(address=OptimismConstants.GAS_ORACLE_CONTRACT_ADDRESS,
                                      abi=OPTIMISM_GAS_ORACLE_ABI)

        gas = oracle.functions.getL1Fee(tx_params['data']).call()

        return gas

    def get_approve_l1_fee(self):
        # Almost doesn't matter in fee calculation
        addr = "0x0000000000000000000000000000000000000000"
        amount = 10

        approve_tx = self._build_approve_transaction(addr, addr, addr, amount)

        return self.get_l1_fee(approve_tx)
