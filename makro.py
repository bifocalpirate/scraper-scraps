#!/usr/bin/env python3

import asyncio
import json
import random
from pyppeteer import launch
from pyppeteer.errors import TimeoutError
from pyppeteer_stealth import stealth,Page
from bs4 import BeautifulSoup
import re
from scraper_lib import BlockedException, HumanAction, get_random_useragent,logger, wrap_payload_with_meta

async def get_session():
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    
    browser = await launch(        
        headless=False, # Headless=True is easier to detect; use False or 'new' if possible        
        args=[            
            '--no-sandbox',
            "--disable-blink-features=AutomationControlled",
            '--user-data-dir=./temp_profile'
            f'--user-agent={user_agent}'
        ],
        executablePath="/snap/bin/chromium"
    )
    page = await browser.newPage()                 
    await stealth(page)    
    await page.evaluateOnNewDocument("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    })
""")
    await page.evaluateOnNewDocument("""
        (() => {
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                // UNMASKED_VENDOR_WEBGL
                if (parameter === 37445) return 'Google Inc. (NVIDIA)';
                // UNMASKED_RENDERER_WEBGL
                if (parameter === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                return getParameter.apply(this, arguments);
            };
        })();
    """)

    # 4. Set Client Hints (Crucial for 2026 anti-bot standards)
    await page.setExtraHTTPHeaders({
        'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    })
    return page

async def test_bot():
    page = await get_session()
    human = HumanAction(page)
    try:
        await page.goto("https://fingerprint-scan.com/")
        await save_screen(page,"nosecure.png")
    finally:
        if page:
            await page.browser.close()
            logger.info("Browser closed.")


async def process_page_recursively(page:Page, human:HumanAction, product_name:str, all_products:list, current_page_number:int = 1):                        
    logger.info(f"You are currently on page {current_page_number} ({page.url})")                                     
    fn = f"makro-page-{product_name}-{current_page_number}.html"     
    content = await page.content()
    save_contents_to_file(content,fn)  #jsut save all the page results        
    p  = process_content_for_products(content)
    if len(p) > 0:
        all_products += p

    next_page_selector = f'a[href*="page={current_page_number+1}"]' #this might raise an exception
    
    try:
        await page.waitForSelector(next_page_selector,{"timeout":10000})
        logger.info(f"Waiting 5 seconds before proceeding to page {current_page_number+1}...")
        await asyncio.sleep(random.uniform(3, 5))
        await human.click(next_page_selector)        
        logger.info(f"Clicked. Waiting 2 seconds now on url {page.url}")
        current_page_number += 1
        await asyncio.sleep(random.uniform(2, 4))
        await process_page_recursively(page,human,product_name, all_products,current_page_number)
    except TimeoutError: #no next page selector
        return all_products
    except Exception as e:
        logger.error(f"{e}")
        await save_screen(page,"makro-exception.png")

async def search(product_name:str):    
    page = await get_session()    
    human = HumanAction(page)
    product_list = []
    try:     
        await page.goto("https://www.makro.co.za",{'waitUntil': 'domcontentloaded', 'timeout': 15000})                                
        search_input = 'input[title="Search Makro"]'            
        try:
            await page.waitForSelector(search_input)    
        except TimeoutError:
            await asyncio.sleep(random.uniform(3, 5))
            pass
            #raise BlockedException                        
        await human.type(search_input,product_name)
        await page.keyboard.press("Enter")               
        await asyncio.sleep(random.uniform(3, 5))            
        await check_is_blocked(page)
        with open(f"makro.first.page.clicked-{product_name}.html","w") as f:
            f.write(await page.content())                            
        await process_page_recursively(page,human, product_name,product_list,1)
        result = wrap_payload_with_meta(product_list,"makro")
        #write the product list to file
        fn = f"makro-{product_name}.json"
        with open(fn,"w") as f:
            json.dump(result,f)        
        logger.info("Run completed!")
    except BlockedException:
        logger.error("MAKRO blocked you or is unable to process searches at the moment. See makro--exception.png")
        await save_screen(page,"makro-blocked-you.png")    
    except Exception as e:
        logger.error(f"Got an exception... {e}")
        logger.error(page.url)
        await save_screen(page,"makro--exception.png")
    finally:
        if page:
            await page.browser.close()
            logger.info("Makro browser closed.")

async def check_is_blocked(page:Page):
    if "blocked" in page.url:
        await save_screen(page,"makro-blocked.png")
        raise BlockedException
    
def process_content_for_products(contents:str):    
    soup = BeautifulSoup(contents,"html.parser")    
    products_list=[]        
    product_cards = soup.find_all('div', attrs={'data-id': True})
    for card in product_cards:
        name_tag = card.find('a', title=True)
        product_name = name_tag['title'] if name_tag else "N/A"        
        card_text = card.get_text().lower()
        is_sold_out = card.find_all("span",string="Sold out") is not []
        image_sources = [img['src'] for img in card.find_all('img', src=True)]                
        is_online_only = "available online only" in card_text                
        has_delivery = any("truck" in src for src in image_sources) or "delivery" in card_text                
        has_pickup = any("cart" in src for src in image_sources) or "pickup" in card_text
        if is_online_only:
            has_delivery = False
            has_pickup = False
        size_regex = re.compile(r'(\d+\s*x\s*)?\d+(\.\d+)?\s*(kg|g|l|ml)', re.I)
        size_tag = card.find('div', string=size_regex)
        quantity = size_tag.get_text(strip=True) if size_tag else "N/A"
        price_elements = card.find_all(string=re.compile(r'R\s*\d+'))
        raw_prices = [p.strip() for p in price_elements]
        current_price = "N/A"
        old_price = None
        if len(raw_prices) >= 1:
            current_price = raw_prices[0]
        if len(raw_prices) >= 2:
            old_price = raw_prices[1]
        discount_tag = card.find(string=re.compile(r'% off'))
        discount = discount_tag.strip() if discount_tag else None
        products_list.append({
            "name": product_name,
            "quantity": quantity,
            "current_price": current_price,
            "old_price": old_price,
            "discount": discount,
            "is_sold_out":is_sold_out,
            "on_sale": True if discount else False,
            "fulfillment": {
                "online_only": is_online_only,
                "delivery_available": has_delivery ,
                "pickup_available": has_pickup 
            }
        })        
    logger.info(f"Page content processed. Found {len(products_list)} products.")
    return products_list
    
async def save_screen(page:Page, fp:str):        
    await page.screenshot({'path': fp})

def save_contents_to_file(content:str,fn:str):
    with open(fn,"w") as f:
        f.write(content)

if __name__=="__main__":        
    asyncio.run(search("5l water"))    
    #asyncio.run(search("peanut butter"))
    #asyncio.run(search("chickpeas"))
    #asyncio.run(test_bot())