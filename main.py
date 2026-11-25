#!/usr/bin/env python3
"""Tiny trend bot for the make.fun bars-replay/v1 harness.

Strategy (paper trading only, no real money, no network):
  * Start long: on the very first batch, buy every symbol at 14% of
    equity. A trend bot that waits for its moving averages to warm up
    misses the opening move, and in a rising market that lag alone
    loses to buy-and-hold, so the bot begins invested like the
    baseline and lets the trend rules take over from there.
  * Trend filter per asset: EMA fast (4h) vs EMA slow (24h) on the
    hourly close. Stay long while the fast EMA is above the slow EMA;
    exit to cash when it crosses below.
  * Trailing stop: sell a position that falls 6% below its highest
    close since entry, so a sharp drop exits even before the slow
    crossover fires.
  * Position size is 14% of current equity per symbol (cap 25%),
    at most one order per symbol per bar, long only, no leverage.

All state comes from the harness itself: closes from each batch,
fills for entry prices, and the account snapshot for cash and
positions. The bot is fully deterministic: fixed alphabetical
symbol order, no randomness, no wall clock, no dict/set iteration
order dependence.
"""

import json
import sys

FAST_SPAN = 4
SLOW_SPAN = 24
TARGET_BPS = 1400          # 14% of equity per position
MAX_SLIPPAGE_BPS = 100     # 1% cap; real impact is far smaller
MIN_NOTIONAL = 1000000     # $1 in micro-USDC
TRAIL_NUM = 94             # sell when close < peak * 94 / 100
TRAIL_DEN = 100
ENTRY_WARMUP_BARS = 9      # trend entries need 9 closes of history
EXIT_WARMUP_BARS = 5       # trend exits need 5 closes of history


class AssetState:
    """Per-symbol trend state; prices are raw scaled integers."""

    def __init__(self):
        self.fast = None      # fast EMA as float over scaled closes
        self.slow = None      # slow EMA as float over scaled closes
        self.bars = 0         # closes seen so far
        self.peak = 0         # highest close since entry (scaled int)
        self.entry = 0        # fill price of the current position

    def update(self, close):
        if self.fast is None:
            self.fast = float(close)
            self.slow = float(close)
        else:
            alpha_fast = 2.0 / (FAST_SPAN + 1)
            alpha_slow = 2.0 / (SLOW_SPAN + 1)
            self.fast = alpha_fast * close + (1.0 - alpha_fast) * self.fast
            self.slow = alpha_slow * close + (1.0 - alpha_slow) * self.slow
        self.bars += 1
        if close > self.peak:
            self.peak = close

    def trending_up(self):
        return self.fast is not None and self.fast > self.slow

    def trailing_hit(self, close):
        return self.peak > 0 and close * TRAIL_DEN < self.peak * TRAIL_NUM


class Bot:
    def __init__(self):
        self.symbols = []          # alphabetical, fixed order
        self.state = {}            # symbol -> AssetState
        self.cash = 0              # micro-USDC, from account snapshot
        self.equity = 0            # micro-USDC, from account snapshot
        self.positions = {}        # symbol -> qty (int, scaled units)

    def on_hello(self, msg):
        names = [s["symbol"] for s in msg.get("symbols", [])]
        self.symbols = sorted(names)
        self.state = {name: AssetState() for name in self.symbols}
        capital = msg.get("capital", {})
        self.cash = int(capital.get("quote_units", "0"))
        self.equity = self.cash

    def on_batch(self, msg):
        seq = msg["seq"]
        account = msg.get("account", {})
        self.cash = int(account.get("cash_quote_units", "0"))
        self.equity = int(account.get("equity_quote_units", str(self.cash)))
        self.positions = {}
        for pos in account.get("positions", []):
            qty = int(pos.get("qty", "0"))
            if qty > 0:
                self.positions[pos["symbol"]] = qty
        closes = {}
        for bar in msg.get("bars", []):
            symbol = bar["symbol"]
            if symbol not in self.state:
                continue
            close = int(bar["c"])
            closes[symbol] = close
            self.state[symbol].update(close)
        for fill in msg.get("fills", []):
            if fill.get("status") != "filled":
                continue
            symbol = fill["symbol"]
            if symbol not in self.state:
                continue
            if fill.get("side") == "buy":
                price = int(fill.get("price", "0"))
                if price > 0:
                    self.state[symbol].entry = price
                    if price > self.state[symbol].peak:
                        self.state[symbol].peak = price
        return self.decide(seq, closes)

    def decide(self, seq, closes):
        orders = []
        cash_plan = self.cash
        for symbol in self.symbols:
            st = self.state[symbol]
            qty = self.positions.get(symbol, 0)
            if qty > 0:
                close = closes.get(symbol, 0)
                exit_trend = st.bars >= EXIT_WARMUP_BARS and not st.trending_up()
                exit_trail = close > 0 and st.trailing_hit(close)
                if exit_trend or exit_trail:
                    orders.append({
                        "side": "sell",
                        "client_id": "s-%s-%d" % (symbol, seq),
                        "symbol": symbol,
                        "qty": str(qty),
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    })
                    st.peak = 0
                    st.entry = 0
                continue
            first_bar = st.bars == 1
            trend_entry = st.bars >= ENTRY_WARMUP_BARS and st.trending_up()
            if not (first_bar or trend_entry):
                continue
            notional = self.equity * TARGET_BPS // 10000
            if notional > cash_plan:
                notional = cash_plan
            if notional < MIN_NOTIONAL:
                continue
            orders.append({
                "side": "buy",
                "client_id": "b-%s-%d" % (symbol, seq),
                "symbol": symbol,
                "notional_quote_units": str(notional),
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            })
            cash_plan -= notional
        return {"type": "reply", "seq": seq, "orders": orders}


def main():
    bot = Bot()
    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        kind = msg.get("type")
        if kind == "hello":
            bot.on_hello(msg)
        elif kind == "batch":
            reply = bot.on_batch(msg)
            out.write(json.dumps(reply, separators=(",", ":")) + "\n")
            out.flush()
        elif kind == "done":
            break


if __name__ == "__main__":
    main()
