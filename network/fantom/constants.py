import os
from dotenv import load_dotenv

load_dotenv()


class FantomConstants:
    NAME = "Fantom"
    NATIVE_TOKEN = "FRM"
    RPC = os.getenv("FANTOM_RPC")
    CHAIN_ID = 250
    STARGATE_CHAIN_ID = 112

    # Contracts
    USDC_CONTRACT_ADDRESS = "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75"
    USDC_DECIMALS = 6

    STARGATE_ROUTER_CONTRACT_ADDRESS = "0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6"

    APPROVE_GAS_LIMIT = 100_000
