import random

from base.errors import NotSupported


class BTCbConstants:
    BTCB_CONTRACT_ADDRESS = "0x2297aEbD383787A160DD0d9F71508148769342E3"
    BTCB_BASE_AVALANCHE_CONTRACT_ADDRESS = "0x152b9d0FdC40C096757F570A51E494bd4b943E50"

    BRIDGE_GAS_LIMIT = {
        'Ethereum': (300_000, 400_000),
        'Arbitrum': (2_000_000, 3_000_000),
        'Optimism': (300_000, 400_000),
        'Polygon': (300_000, 400_000),
        'BSC': (250_000, 300_000),
        'Avalanche': (300_000, 350_000)
    }

    @staticmethod
    def get_max_randomized_bridge_gas_limit(network_name: str) -> int:
        return BTCbConstants.BRIDGE_GAS_LIMIT[network_name][1]

    @staticmethod
    def get_randomized_bridge_gas_limit(network_name: str) -> int:
        if network_name not in BTCbConstants.BRIDGE_GAS_LIMIT:
            raise NotSupported(f"{network_name} isn't supported by get_randomized_bridge_gas_limit()")

        return random.randint(BTCbConstants.BRIDGE_GAS_LIMIT[network_name][0],
                              BTCbConstants.BRIDGE_GAS_LIMIT[network_name][1])
