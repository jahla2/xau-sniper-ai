from xau_sniper_ai.models import Candle, MarketSnapshot


def c(ts: int, o: float, h: float, l: float, close: float) -> Candle:
    return Candle(ts=ts, open=o, high=h, low=l, close=close, volume=100)


def trend(start: float, n: int, step: float, ts0: int = 1_000) -> list[Candle]:
    out=[]
    price=start
    for i in range(n):
        nxt=price+step
        out.append(c(ts0+i*300, price, max(price,nxt)+0.25, min(price,nxt)-0.25, nxt))
        price=nxt
    return out


def market(m5: list[Candle], bid: float = 100.0, ask: float = 100.2, symbol: str = "XAUUSD") -> MarketSnapshot:
    return MarketSnapshot(symbol=symbol, timeframe="M5", bid=bid, ask=ask, m5=m5)
