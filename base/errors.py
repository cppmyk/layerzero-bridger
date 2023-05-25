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


class ExchangeError(BaseError):
    pass


class NotWhitelistedAddress(ExchangeError):
    pass
