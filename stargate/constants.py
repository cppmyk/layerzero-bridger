import random

from base.errors import NotSupported


class StargateConstants:
    SWAP_GAS_LIMIT = {
        'Ethereum': (580_000, 630_000),
        'Arbitrum': (3_000_000, 4_000_000),
        'Optimism': (700_000, 900_000),
        'Fantom': (800_000, 1_000_000),
        'Polygon': (580_000, 630_000),
        'BSC': (560_000, 600_000),
        'Avalanche': (580_000, 700_000)
    }

    POOLS = {
        "USDC": 1,
        "USDT": 2,
        "DAI": 3,
        "BUSD": 5,
        "FRAX": 7,
        "USDD": 11,
        "ETH": 13,
    }

    @staticmethod
    def get_max_randomized_swap_gas_limit(network_name: str) -> int:
        return StargateConstants.SWAP_GAS_LIMIT[network_name][1]

    @staticmethod
    def get_randomized_swap_gas_limit(network_name: str) -> int:
        if network_name not in StargateConstants.SWAP_GAS_LIMIT:
            raise NotSupported(f"{network_name} isn't supported by get_randomized_swap_gas_limit()")

        return random.randint(StargateConstants.SWAP_GAS_LIMIT[network_name][0],
                              StargateConstants.SWAP_GAS_LIMIT[network_name][1])
