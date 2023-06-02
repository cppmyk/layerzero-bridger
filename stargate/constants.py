import random

from base.errors import NotSupported


class StargateConstants:
    SWAP_GAS_LIMIT = {
        'Ethereum': 600_000,
        'Arbitrum': 5_000_000,
        'Optimism': 1_000_000,
        'Fantom': 1_000_000,
        'Polygon': 600_000,
        'BSC': 600_000,
        'Avalanche': 600_000
    }
    RANDOMIZE_PERCENT = 0.05  # Percent of gas limit random

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
        return int(StargateConstants.SWAP_GAS_LIMIT[network_name] * (1 + StargateConstants.RANDOMIZE_PERCENT))

    @staticmethod
    def get_randomized_swap_gas_limit(network_name: str) -> int:
        if network_name not in StargateConstants.SWAP_GAS_LIMIT:
            raise NotSupported(f"{network_name} isn't supported by get_swap_gas_limit()")

        min_rand = int(StargateConstants.SWAP_GAS_LIMIT[network_name] * (1 - StargateConstants.RANDOMIZE_PERCENT))
        max_rand = int(StargateConstants.SWAP_GAS_LIMIT[network_name] * (1 + StargateConstants.RANDOMIZE_PERCENT))

        return random.randint(min_rand, max_rand)
