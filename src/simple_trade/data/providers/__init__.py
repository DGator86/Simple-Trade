from simple_trade.data.providers.alpaca import AlpacaProvider
from simple_trade.data.providers.base import Provider, ProviderError
from simple_trade.data.providers.massive import MassiveProvider
from simple_trade.data.providers.tradier import TradierProvider

PROVIDERS: dict[str, type[Provider]] = {
    "massive": MassiveProvider,
    "alpaca": AlpacaProvider,
    "tradier": TradierProvider,
}

__all__ = ["PROVIDERS", "AlpacaProvider", "MassiveProvider", "Provider", "ProviderError",
           "TradierProvider"]
