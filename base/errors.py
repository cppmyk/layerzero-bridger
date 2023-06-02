class BaseError(Exception):
    pass


class NotSupported(BaseError):
    pass


class NotEnoughNativeTokenBalance(BaseError):
    pass


class NotEnoughStablecoinBalance(BaseError):
    pass


class StablecoinNotSupportedByChain(BaseError):
    pass


class ConfigurationError(BaseError):
    pass


# -------- Blockchain error --------

class BlockchainError(BaseError):
    pass


class TransactionNotFound(BlockchainError):
    pass


class TransactionFailed(BlockchainError):
    pass


# -------- Exchange error --------

class ExchangeError(BaseError):
    pass


class NotWhitelistedAddress(ExchangeError):
    pass


class WithdrawCanceled(ExchangeError):
    pass


class WithdrawTimeout(ExchangeError):
    pass


class WithdrawNotFound(ExchangeError):
    pass
