from xau_sniper_ai.models import Candle, MarketSnapshot


def c(ts: int, o: float, h: float, l: float, close: float) -> Candle:
    return Candle(ts=ts, open=o, high=h, low=l, close=close, volume=100)


def trend(start: float, n: int, step: float, ts0: int = 1_000) -> list[Candle]:
    out=[]
    price=start
    for i in range(n):
        nxt=price+step
        out.append(c(ts0+i*60, price, max(price,nxt)+0.25, min(price,nxt)-0.25, nxt))
        price=nxt
    return out


def neutral_market(m1: list[Candle], bid: float = 100.0, ask: float = 100.2) -> MarketSnapshot:
    base = trend(90, 12, 0.4)
    return MarketSnapshot(symbol="XAUUSD", bid=bid, ask=ask, m1=m1, m5=base, m15=base, h1=base)
