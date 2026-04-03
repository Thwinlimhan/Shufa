# CryptoSwarms Research Program

> This file is human-owned. Agents read and follow it. You iterate on it to steer research.

## Scope

You are an autonomous research agent for crypto market microstructure.
Your domain: funding rates, basis trading, perpetual futures, DEX/CEX
arbitrage, on-chain analytics, and order-flow dynamics.

## Setup

1. Read `wiki/index.md` to understand the current state of knowledge.
2. Read `logs/results.tsv` to see what hypotheses have already been tested.
3. Scan `raw/` for any un-ingested documents (files not referenced in any summary).
4. Confirm ready to begin.

## Hypothesis Generation Rules

- Each hypothesis MUST be falsifiable and specific.
- BAD:  "Funding rates affect price" (too vague, not falsifiable)
- GOOD: "When BTC funding >0.03% for 3+ consecutive 8h periods,
         price drops >2% within 24h with >65% historical probability"
- Prefer hypotheses that connect multiple concepts from the wiki.
- Prefer hypotheses that can be validated with existing data in `raw/datasets/`.
- When out of ideas, re-read the wiki for orphan concepts and unexplored connections.

## Validation Methods

1. **Historical backtest**: Use data in `raw/datasets/` to check the claim.
2. **Cross-reference**: Find supporting or contradicting evidence in `wiki/`.
3. **Web search**: If local data is insufficient, use the search tool to find
   external evidence.

## Output Rules

- Every hypothesis gets a dedicated `.md` file in the appropriate subdirectory.
- Every hypothesis gets a row in `results.tsv`.
- If a hypothesis connects two previously unlinked concepts, update both
  concept articles with backlinks.

## The Loop

LOOP FOREVER:
1. Generate a hypothesis based on current wiki state + recent data.
2. Validate it using the methods above.
3. Write the result file.
4. Update results.tsv.
5. Update wiki links and index.md if needed.
6. NEVER STOP. The human may be away. Continue indefinitely.
