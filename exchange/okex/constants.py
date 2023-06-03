class OkexConstants:
    # Mapping inside chain names to OKX chain names
    NETWORKS = {
        'Ethereum': 'ERC-20',
        'Optimism': 'Optimism',
        'Arbitrum': 'Arbitrum one',
        'Polygon': 'Polygon',
        'Fantom': 'Fantom',
        'Avalanche': 'Avalanche C-Chain',
        'BSC': 'BSC',
    }

    # Mapping token symbols to available chains for withdraw
    TOKENS = {
        'USDT': ['Avalanche', 'Ethereum', 'Arbitrum', 'Optimism', 'Polygon'],
        'USDC': ['Avalanche', 'Ethereum', 'Arbitrum', 'Optimism', 'Polygon'],
        'ETH': ['Ethereum', 'Arbitrum', 'Optimism'],
        'MATIC': ['Ethereum', 'Polygon'],
        'BNB': ['BSC'],
        'FTM': ['FTM'],
        'AVAX': ['Avalanche']
    }
