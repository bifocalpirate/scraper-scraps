#!/usr/bin/env python3
from pyppeteer import launch
from pyppeteer_stealth import stealth
from bs4 import BeautifulSoup
import requests
import re
from scraper_lib import get_headers_dictionary, get_random_useragent

SLEEP_DELAY = 2


def get_catfood_price(url:str = "https://www.absolutepets.com/shop/product/cat-food/lokuno-adult-cat-food"):    
    r = requests.get(url,headers=get_headers_dictionary("headers_lokuno.txt"))    
    c = BeautifulSoup(r.content,"html.parser")    
    option = c.find("option",string=re.compile(r"7\.5kg"))    				
    print(option["data-price"])

get_catfood_price()




