# Bank Financial Ratio Analysis

## At a glance

- **Question:** which big US banks earn their returns by running the business well, and which get them by borrowing more?
- **Data:** annual reports of 7 large US banks, 2021 to 2025, pulled from the SEC with code.
- **Method:** ratios, rankings and year-over-year change calculated in SQL. ROE is split into its two parts: profit earned on assets (ROA) and leverage.
- **Finding:** ranking by ROE alone puts Goldman Sachs ahead of Capital One. Capital One earns the most on its assets (ROA 1.37%, 1st of 7) and Goldman Sachs is 5th (0.92%). Goldman's ROE is lifted by the highest leverage of the group.

![Where each bank's ROE comes from](roe_breakdown.png)

## Why this question

Banks are usually compared on one number, ROE (return on equity). But a bank can raise its ROE in two ways: earn more profit from what it owns, or borrow more. The second way adds risk. An investor or a credit analyst needs to know which one they are looking at.

I started this project comparing three banks to understand how bank ratios work. The most interesting thing I noticed was that two banks can show a similar ROE and get there in different ways. So I rebuilt the project around that one question, with more banks and more years.

## How to read the numbers

| Ratio | Formula | In plain words |
|---|---|---|
| ROE | Profit / Shareholders' money | What the owners earn on what they put in |
| ROA | Profit / Total assets | How well the bank uses everything it owns |
| Leverage | Total assets / Shareholders' money | 12 means 12 dollars of assets for every 1 dollar of the bank's own money |
| Efficiency ratio | Costs / Revenue | What the bank spends to earn 1 dollar. Lower is better |
| NIM | Net interest income / Total assets | What the bank earns from lending (simplified) |

**ROE = ROA x Leverage.** This is the key idea, a standard method called DuPont analysis. It lets you see how much of a bank's ROE comes from the business and how much from leverage.

## What I did

**1. Pulled the data with code.** Six numbers for each bank and year come straight from the SEC's public data service: 7 banks x 5 years x 6 numbers = 210 values, none missing. One thing I had to handle: banks do not all use the same tag for revenue (`Revenues` or `RevenuesNetOfInterestExpense`), so the code tries a short list of tags. I checked JPMorgan's 2025 numbers against its filing.

**2. Loaded it into SQL (DuckDB) as two tables:** `financials` (one row per bank, year and number) and `banks` (name and type of each bank).

**3. Did the analysis in SQL.** The queries are in the notebook and also in [`queries.sql`](queries.sql):

| Query | What it answers | SQL used |
|---|---|---|
| 1 | One row per bank and year | `JOIN`, `CASE WHEN`, `GROUP BY` |
| 2 | The five ratios | calculated columns, a view |
| 3 | ROE rank in each year | `RANK() OVER (PARTITION BY ...)` |
| 4 | Change in ROE from the year before | `LAG()` |
| 5 | Where each bank's ROE comes from | CTEs (`WITH`), `MEDIAN`, `CROSS JOIN`, `RANK()` |
| 6 | Costs and lending margin by bank type | `GROUP BY` on the joined tables |

## Results

Five-year averages, 2021 to 2025:

| Bank | Type | ROE | ROA | Leverage | ROE at typical leverage | Rank by ROE | Rank by ROA |
|---|---|---|---|---|---|---|---|
| JPMorgan Chase | Universal bank | 15.43% | 1.27% | 12.18 | 14.96% | 1 | 2 |
| Morgan Stanley | Investment bank | 12.47% | 1.05% | 11.89 | 12.37% | 2 | 3 |
| Goldman Sachs | Investment bank | 12.40% | 0.92% | 13.58 | 10.84% | 3 | 5 |
| Capital One | Card lender | 10.54% | 1.37% | 7.59 | 16.14% | 4 | 1 |
| Wells Fargo | Universal bank | 10.49% | 0.97% | 10.77 | 11.43% | 5 | 4 |
| Bank of America | Universal bank | 10.04% | 0.89% | 11.24 | 10.48% | 6 | 6 |
| Citigroup | Universal bank | 7.11% | 0.61% | 11.78 | 7.19% | 7 | 7 |

"ROE at typical leverage" is what each bank's ROE would be if it used the leverage of the middle bank in the group (11.78).

**1. JPMorgan's high ROE is earned.** Highest ROE, second-highest ROA, and leverage close to typical. At typical leverage its ROE would still be about 15.0%.

**2. Goldman Sachs gets part of its ROE from borrowing.** 3rd on ROE but 5th on ROA, with the most leverage of the group. About 1.6 points of its ROE come from that extra leverage.

**3. Capital One is the opposite case.** 4th on ROE but 1st on ROA. It uses far less leverage (7.6), so its ROE looks ordinary even though it earns the most from its assets. A caution: a card lender takes more credit risk, so it has to hold more of its own money. It could not simply borrow as much as the others.

**4. Citigroup is last on both measures.** Its leverage is typical, so the weakness is in the business itself.

**5. Bank types work differently.** The card lender earns 6.1% on lending (NIM), the universal banks about 2.0%, and the investment banks 0.6%, because they earn mostly from fees and trading. NIM should only be compared between banks of the same type.

![ROE by year](roe_by_year.png)

## Limits

- Ratios use year-end balance sheet numbers, not averages over the year.
- NIM is simplified (divided by total assets, where banks normally use interest-earning assets).
- 2025 was unusual for Capital One: it bought Discover that year, which roughly doubled its equity and pulled its ROE down to 2.2%.
- Leverage here is a simple accounting measure. Regulators use risk-weighted capital ratios such as CET1, which are not in these data.

## Files

- `Bank.ipynb`: the full notebook (data pull, SQL analysis, charts, conclusion)
- `queries.sql`: the six SQL queries on their own
- `bank_financials.csv`: the numbers pulled from the SEC
- `bank_ratios.csv`: the five ratios for every bank and year
- `roe_breakdown.csv`: the final table shown above
- `roe_breakdown.png`, `roe_by_year.png`: the charts
- `requirements.txt`: the Python packages needed

## How to run this yourself

1. Clone this repo and run `pip install -r requirements.txt`.
2. Open `Bank.ipynb`. In Part 1, put your own name and email in the `headers` line (the SEC asks every program to say who is calling).
3. Run all cells from top to bottom. Part 1 needs internet access. If you skip it, the saved `bank_financials.csv` lets Parts 2 to 4 run on their own.

## Tools

SQL (DuckDB), Python (pandas, requests, matplotlib), SEC EDGAR data.

## About me

Rahul Kulkarni
M.S. Business Analytics, UC San Diego (Rady School of Management)
