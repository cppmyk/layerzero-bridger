class BinanceConstants:
    # Mapping inside chain names to OKX chain names
    NETWORKS = {
        'Ethereum': 'ETH',
        'Optimism': 'OPTIMISM',
        'Arbitrum': 'ARBITRUM',
        'Polygon': 'MATIC',
        'Fantom': 'FTM',
        'Avalanche': 'AVAXC',
        'BSC': 'BSC',
    }

    # Mapping token symbols to available chains for withdraw
    TOKENS = {
        'USDT': ['BSC', 'Avalanche', 'Ethereum', 'Arbitrum', 'Optimism', 'Polygon'],
        'USDC': ['BSC', 'Avalanche', 'Ethereum', 'Polygon'],
        'BUSD': ['BSC', 'Avalanche', 'Optimism', 'Polygon'],
        'ETH': ['BSC', 'Ethereum', 'Arbitrum', 'Optimism'],
        'MATIC': ['BSC', 'Ethereum', 'Polygon'],
        'BNB': ['BSC'],
        'FTM': ['BSC', 'FTM', 'ETH'],
        'AVAX': ['BSC', 'Avalanche']
    }
