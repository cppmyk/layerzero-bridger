from dataclasses import dataclass


@dataclass
class Stablecoin:
    symbol: str
    contract_address: str
    decimals: int
    stargate_chain_id: int
    stargate_pool_id: int
