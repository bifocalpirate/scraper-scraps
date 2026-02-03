import os
from pathlib import Path
import random
import logging.config
from dotenv import load_dotenv
import sys
import time

class BlockedException(Exception):
    """Exception raised for when the scraper is blocked."""
    pass

import asyncio
import random
import math

class HumanAction:
    def __init__(self, page):
        self.page = page
        # Track position because Pyppeteer doesn't expose it easily
        self.cur_x = random.randint(0, 100)
        self.cur_y = random.randint(0, 100)

    async def move_to(self, target_x, target_y):
        steps = random.randint(30, 50)
        # Control points for the Bezier curve
        c1x = self.cur_x + (target_x - self.cur_x) * random.uniform(0.1, 0.4)
        c1y = self.cur_y + (target_y - self.cur_y) * random.uniform(0.1, 0.9)
        c2x = self.cur_x + (target_x - self.cur_x) * random.uniform(0.6, 0.9)
        c2y = self.cur_y + (target_y - self.cur_y) * random.uniform(0.1, 0.9)

        for i in range(steps + 1):
            linear_t = i / steps
            # Sinusoidal easing for velocity
            t = (1 - math.cos(linear_t * math.pi)) / 2
            
            x = (1-t)**3 * self.cur_x + 3*(1-t)**2 * t * c1x + 3*(1-t) * t**2 * c2x + t**3 * target_x
            y = (1-t)**3 * self.cur_y + 3*(1-t)**2 * t * c1y + 3*(1-t) * t**2 * c2y + t**3 * target_y
            
            await self.page.mouse.move(x + random.uniform(-0.5, 0.5), y + random.uniform(-0.5, 0.5))
            await asyncio.sleep(0.002 + (0.008 * (1 - math.sin(linear_t * math.pi))))

        self.cur_x, self.cur_y = target_x, target_y

    async def click(self, selector):
        element = await self.page.waitForSelector(selector)
        rect = await element.boundingBox()
        
        # Pick a random point inside the element (avoiding the exact edges)
        target_x = rect['x'] + random.uniform(rect['width'] * 0.2, rect['width'] * 0.8)
        target_y = rect['y'] + random.uniform(rect['height'] * 0.2, rect['height'] * 0.8)
        
        await self.move_to(target_x, target_y)
        
        # Human-like click: Down -> short pause -> Up
        await self.page.mouse.down()
        await asyncio.sleep(random.uniform(0.06, 0.18))
        await self.page.mouse.up()
    
    async def hold_on(self, selector, duration):
        """
        Moves to a selector and holds the left mouse button down for 'duration' seconds.
        Includes micro-movements to simulate a human hand trembling slightly while holding.
        """
        element = await self.page.waitForSelector(selector)
        rect = await element.boundingBox()
        
        target_x = rect['x'] + random.uniform(rect['width'] * 0.3, rect['width'] * 0.7)
        target_y = rect['y'] + random.uniform(rect['height'] * 0.3, rect['height'] * 0.7)
        
        await self.move_to(target_x, target_y)
        
        # Press down
        await self.page.mouse.down()
        
        # Hold for duration, but add micro-jitters 
        # (Humans don't stay perfectly still at the pixel level)
        end_time = asyncio.get_event_loop().time() + duration
        while asyncio.get_event_loop().time() < end_time:
            # Subtle hand trembling (0.1 to 0.3 pixel movement)
            await self.page.mouse.move(
                target_x + random.uniform(-0.3, 0.3), 
                target_y + random.uniform(-0.3, 0.3)
            )
            await asyncio.sleep(random.uniform(0.05, 0.1))
            
        await self.page.mouse.up()

    async def type(self, selector, text):
        await self.click(selector) # Focus the field first
        for char in text:
            await self.page.keyboard.sendCharacter(char)
            # Variable typing speed with occasional "thinking" pauses
            delay = random.uniform(0.05, 0.2)
            if random.random() < 0.1: # 10% chance of a longer pause
                delay += random.uniform(0.3, 0.6)
            await asyncio.sleep(delay)

dotenv_path = Path('.env')

if (len(sys.argv) == 2):
  dotenv_path = sys.argv[1]

load_dotenv(dotenv_path=dotenv_path)

EASYEQUITIES_USERNAME = os.getenv("EASYEQUITIES_USERNAME")
EASYEQUITIES_PASSWORD = os.getenv("EASYEQUITIES_PASSWORD")
EASYEQUITIES_PORTFOLIO_IDS = os.getenv("EASYEQUITIES_PORTFOLIO_IDS")
EASYEQUITIES_ID_NUMBER = os.getenv("EASYEQUITIES_ID_NUMBER")
EASYEQUITIES_DOWNLOAD_PATH = os.getenv("EASYEQUITIES_DOWNLOAD_PATH")
EASYEQUITIES_USD_ZAR=os.getenv("EASYEQUITIES_USD_ZAR")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s %(module)s:%(lineno)d: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": "app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)
# https://www.useragents.me/ for json (updated weekly)
user_agents = [{"ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.10 Safari/605.1.1", "pct": 43.03}, {"ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.3", "pct": 21.05}, {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3", "pct": 17.34}, {"ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3", "pct": 3.72}, {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Trailer/93.3.8652.5", "pct": 2.48}, {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.", "pct": 2.48}, {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.", "pct": 2.48}, {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/117.0.0.", "pct": 2.48}, {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.", "pct": 1.24}, {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.1958", "pct": 1.24}, {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.", "pct": 1.24}, {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.3", "pct": 1.24}]

def get_random_useragent(ua="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"):    
    return random.choice(user_agents)["ua"] if not ua else ua 

def wrap_payload_with_meta(payload:dict, source:str):
    return {"payload":payload,"source":f"source","meta":{"runner":"system", "extract_time_gmt":f"{time.asctime(time.gmtime())}"}}