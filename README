# Functions to scrape specific websites

Started out with a script to monitor the price of a bar of soap, ended up recalculating NAV.

## EasyEquities
- Download all statements, Remove password on statement files
- Download all holdings by portfolio
- Fnd total contributions to a portfolio (if you want to know how much you funded the portfolio with)
- Get cash holdings
- Get NAV per portfolio as a JSON file (easy to load into a plotter)

## ArcStores
- Scan arcstores get price by product id
## PicknPay
- Download all specials from pnp by store id
## Makro
- Get product prices of products matching a search search string for makro store
## Lokuno
- Get price of lokuno cat food

# Tech stack
- Combination of headless Chromium controlled by `pyppeteer` using random User-Agents, and plain old requests.
- Parse content using BeautifulSoup

# Roadmap?
- Dump all of this into a database and subscribe to price changes
- Download catalogues, use LayoutLM + some kind of OCR 