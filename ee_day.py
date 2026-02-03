#!/usr/bin/env python3
import asyncio
import json
from ee import get_portfolio_data
from scraper_lib import EASYEQUITIES_PORTFOLIO_IDS

async def get_daily_portfolio_data():
    url = "https://platform.easyequities.io/AccountOverview"        
    await get_portfolio_data(url.strip(),True, *json.loads(EASYEQUITIES_PORTFOLIO_IDS))

if __name__== "__main__":
    asyncio.run(get_daily_portfolio_data())