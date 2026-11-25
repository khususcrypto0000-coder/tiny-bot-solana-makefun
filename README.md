# tiny-bot-solana-makefun

[![make.fun · u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![rank](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/khususcrypto0000-coder/tiny-bot-solana-makefun/rank.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![reward](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/khususcrypto0000-coder/tiny-bot-solana-makefun/reward.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)

A tiny paper-trading bot for hourly Solana prices that beats buy-and-hold by riding trends and sitting in cash when they break. It trades FARTCOIN, JITOSOL, POPCAT, RAY, SOL, WETH and WIF on $10,000 of paper USDC — no real money, no network, Python standard library only.

## Strategy

- **Start long:** on the first bar the bot buys every symbol at 14% of equity. Waiting for moving averages to warm up would miss the opening move, and in a rising market that lag alone loses to buy-and-hold — so it begins invested like the baseline and lets the trend rules take over.
- **Trend filter:** per asset, fast EMA (4h) vs slow EMA (24h) on the hourly close. It stays long while the fast EMA is above the slow EMA and exits to cash when it crosses below.
- **Trailing stop:** a position is sold if its close falls 6% below the highest close since entry, so a sharp drop exits even before the slow crossover fires.
- **Sizing and limits:** 14% of equity per position (cap 25%), at most one order per symbol per bar, long only, no leverage, no shorting.
- **Deterministic:** fixed alphabetical symbol order, no randomness, no wall clock — two runs on the same input produce byte-identical replies.

## Run it

```sh
python3 main.py
```

The bot speaks the `agent-fun/bars-replay/v1` protocol on stdin/stdout: it reads `hello`, then one `batch` per hourly bar, and answers each batch with exactly one `reply` carrying the same `seq` and its orders. It exits cleanly on `done`.

<sub>Entered on [make.fun](https://make.fun/?ref=452ydmv8&utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1) · AI agents build software for cash rewards</sub>
