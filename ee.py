#!/usr/bin/env python3
import asyncio
from PyPDF2 import PdfReader, PdfWriter
from pyppeteer import launch 
from pyppeteer_stealth import stealth,Page
from scraper_lib import EASYEQUITIES_DOWNLOAD_PATH, EASYEQUITIES_PASSWORD, EASYEQUITIES_USD_ZAR, EASYEQUITIES_USERNAME, get_random_useragent, logger, wrap_payload_with_meta
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import pdfplumber
import glob
from pathlib import Path
import os

date_format_string = "%a %b %d %H:%M:%S %Y"

SLEEP_DELAY = 5
SAVE_CAPTURES = False

async def get_session():
    browser = await launch(headless=True,args=["--no-sandbox"])    
    page = await browser.newPage()             
    await page.setUserAgent(get_random_useragent())    
    await stealth(page)    
    await login(page,EASYEQUITIES_USERNAME,EASYEQUITIES_PASSWORD)
    return page

async def get_portfolio_data(url:str, logout=True, *portfolio_ids:dict):    
    page = await get_session()        
    content = ""
    results = []
    try:                
        await page.goto(url,{'waitUntil': ['domcontentloaded'],'timeout':60000})                            
        await save_screen(page,"afterlogin.png")
        for item in portfolio_ids:                                       
            portfolio_id, desc = item.values()
            await page.click(f'div[data-id="{portfolio_id}"]') 
            await save_screen(page, f'{portfolio_id}_dashboard-landing.png')        
            await page.waitForNavigation()
            await save_screen(page,  f'{portfolio_id}_history.png')        
            await page.waitForSelector("#loadHoldings")
            await save_screen(page, f'{portfolio_id}_dashboard-e.png')
            await page.click("#loadHoldings")        
            time.sleep(SLEEP_DELAY)        
            content = await page.content()                   
            results.append(process_portfolio_data(content,portfolio_id,desc))      
        rems = wrap_payload_with_meta(results,"easyequities")
        formatted_date = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        with open(f"{EASYEQUITIES_DOWNLOAD_PATH}/ee_ALL_portfolio_{formatted_date}.json","w",encoding="utf-8") as f:
            json.dump(rems,f,indent=4, ensure_ascii=False)     
        logger.info("Data retrieved.")       
    finally:
        if logout:
            await page.goto("https://platform.easyequities.io/Account/SignOut")                     
            logger.info("Logged out...")
            await page.browser.close()


async def remove_password(input_folder:str, wildcard:str, output_folder:str,  password:str):
    files = glob.glob(f"{input_folder}{wildcard}")
    for file in files:
        reader = PdfReader(file)
        if (reader.is_encrypted):
            reader.decrypt(password)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        filename = Path(file).name
        output_file = f"{output_folder}{filename}"
        with open(output_file,"wb") as f:
            writer.write(f)        
    logger.info("Done removing password from files.")

async def get_all_contribution_values(input_folder:str):
    files = glob.glob(f"{input_folder}*.pdf")
    result = []
    for file in files:  
        r = await get_contributions_from_pdf(file)
        if r:      
            result.append(r)
    items = sum([r for r in result if r],[])
    sorted_items = sorted(items, key=lambda x: x['month'])
    logger.info(sorted_items)

async def scan_for_capital_contributions(input_folder:str):
    files = glob.glob(f"{input_folder}*.pdf")
    result = []
    for file in files:  
        logger.debug(f"Scanning file {file}")
        r = await scan_for_capital_contribution(file)
        if r:      
            logger.info(r)
            result.append(r)    
    return result

async def scan_for_capital_contribution(input_file:str):
    with pdfplumber.open(input_file) as pdf:
        page = pdf.pages[3]
        tables = page.extract_tables()        
        for table in tables:
            for row in table:                                
                if "Capital contribution" in row:                    
                    month,  value = row[0],row[3]
                    return {"month":month,"value":value}
        return None                    

async def get_contributions_from_pdf(file_name):
    found_contributions = []    
    try:        
        with pdfplumber.open(file_name) as pdf:        
            if len(pdf.pages) < 3:
                return found_contributions
            
            page = pdf.pages[2]
            table = page.extract_table()
            
            if not table:
                return found_contributions            
            headers = table[1] 
            
            for row in table:                                
                row_label = str(row[0]).strip()
                
                if "Contributions" in row_label:                                        
                    for month, value in zip(headers[1:], row[1:]):                        
                        if month and value and value.strip() != "0":
                            clean_month = datetime.strptime("01 " + month.replace("\n", " ").strip(),"%d %b %Y")
                            found_contributions.append({
                                "month": clean_month,
                                "amount": value.strip()
                            })
                    break
    except Exception as e:
        logger.error(f"Error processing {os.path.basename(file_name)}: {e}")    
    return found_contributions

async def download_statements(logout=True):
    page = await init_session()
    try:
        await page.goto("https://platform.easyequities.io/Statement")        
        content = BeautifulSoup(await page.content(),"html.parser")
        buttons = content.find_all('a',class_ ='statementDownloadBtn')                
        download_path = EASYEQUITIES_DOWNLOAD_PATH
        cdp = await page.target.createCDPSession()
        await cdp.send('Page.setDownloadBehavior', {
            'behavior': 'allow',
            'downloadPath': download_path
        })
        
        for btn in buttons:
            target_url = btn.get('data-url')
            target_filename = btn.get('data-filename')
            await page.evaluate("""async (url, filename) => {
        $.ajax({
            type: "GET",
            url: url,
            beforeSend: function(request) {
                request.overrideMimeType('text/plain; charset=x-user-defined');
            },
            success: function(response) {
                var dataArray = new Uint8Array(response.length);
                for (var i = 0; i < response.length; i++) {
                    dataArray[i] = response.charCodeAt(i);
                }
                var blob = new Blob([dataArray.buffer], { type: "application/pdf" });
                let link = document.createElement('a');
                link.download = filename;
                link.href = URL.createObjectURL(blob);
                link.click();
                setTimeout(() => URL.revokeObjectURL(link.href), 100);
            }
        });
    }""", target_url, target_filename)                 
        await asyncio.sleep(5)
    finally:
        if logout:
            await page.goto("https://platform.easyequities.io/Account/SignOut")                     
            logger.info("Logged out...")
            await page.browser.close()    

async def login(page:Page, username:str, password:str):            
    await page.goto('https://identity.openeasy.io')    
    await page.waitForSelector('#user-identifier-input')
    await page.type('#user-identifier-input', username)    
    await page.type('#Password', password)    
    await asyncio.gather(
        page.waitForNavigation(),
        page.click('#SignIn'),
    )                
    await page.goto("https://platform.easyequities.io/AccountOverview")      
    time.sleep(SLEEP_DELAY)          
    cookies = await page.cookies()    
    with open('cookies.json', 'w') as f:
        json.dump(cookies, f)
    return cookies
    
async def save_screen(page:Page, fp:str):
    if (SAVE_CAPTURES):
        f = f"{EASYEQUITIES_DOWNLOAD_PATH}/{fp}"
        print(f)
        await page.screenshot({'path': f})

def save_content(content:str):
    with open("ee.html","w") as f:
            f.write(content)

async def parse_portfolio_files(download_folder:str, fn_mask:str, usd_to_zar_rate=16.20):
    # Initialize the structure as requested
    result = {
        "ZAR": [],
        "USD": [],
        "TFSA": [],
        "CASH": [] 
    }

    files = glob.glob(f"{download_folder}{fn_mask}")
    files = sorted(files)

    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)        
        
        raw_date = data['meta']['extract_time_gmt']
        date_obj = datetime.strptime(raw_date, "%a %b %d %H:%M:%S %Y")
        formatted_date = date_obj.strftime("%Y-%m-%d")
        
        total_combined_cash_zar = 0.0        
        for account in data['payload']:
            acc_type = account['desc']             

            def clean_val(val_str):
                return float(val_str.replace('R', '').replace('$', '').replace(' ', '').replace(',', ''))
            
            holdings_raw = sum(clean_val(h['current_value']) for h in account['holdings'])
            cash_raw = clean_val(account['cash'])            
            
            total_account_value = holdings_raw + cash_raw                        
            if acc_type == "USD":                
                total_converted = round(total_account_value * usd_to_zar_rate, 2)
                cash_converted = cash_raw * usd_to_zar_rate
            else:                
                total_converted = round(total_account_value, 2)
                cash_converted = cash_raw

            total_combined_cash_zar += cash_converted
            
            if acc_type in result:
                result[acc_type].append({formatted_date: total_converted})        
        
        result["CASH"].append({formatted_date: round(total_combined_cash_zar, 2)})
    logger.info(result)
    return result

async def get_portfolio_total(download_folder:str, fn_mask:str):
    files = glob.glob(f"{download_folder}{fn_mask}")
    files = sorted(files)
    results = {}    
    cash = 0
    usd_zar = float(EASYEQUITIES_USD_ZAR)
    for file in files:        
        with open(file,"r") as f:
            c = dict(json.load(f))
            dt = datetime.strptime(c["meta"]["extract_time_gmt"], date_format_string)                                                
            time_key = dt.strftime("%Y-%m-%d")                        
            cash = 0
            money_value = 0
            for payload in c["payload"]:                                                
                #logger.info(f"------------------- {payload["desc"]} portfolio")                
                if "cash" in payload:
                    m = float(payload["cash"].replace("R","").replace("$","").replace(" ",""))                                            
                    if payload["desc"] == "USD":
                        cash += (usd_zar * m)  #do conversion to ZAR
                    else:
                        cash += m
                    logger.info(f"-------------------")
                    logger.info(f"Cash of R {cash:.2f} in {payload["desc"]} ")
                    logger.info(f"-------------------")
                for holding in payload["holdings"]: #add up the holdigs
                    holding_nominal = float(holding["current_value"].replace(" ","").replace("R","").replace("$",""))                                        
                    if payload["desc"] == "USD": # need to convert currency                        
                        holding_nominal = (holding_nominal *  usd_zar)
                    
                    money_value += holding_nominal
                    logger.info(f"Adding {holding["name"]} {holding_nominal:.2f} ")                                        
            cash += money_value
        results[time_key] = f"{cash:.2f}"  # replace with the most recent value   
        money_value = 0
    logger.info(results)
    return results                    

def process_portfolio_data(content:str, fn:str,desc:str):                
    soup = BeautifulSoup(content,"html.parser")
    holdings_list = []
    funds_element = soup.find('span', {'data-bind': 'text: fundSummaryItemsHeading().value, css: fundSummaryItemsHeading().cssClass'})
    cash_value = funds_element.text    
    # Find all rows containing stock data
    rows = soup.find_all('div', class_='holding-body-table-row')
    for row in rows:
        try:            
            name = row.find('div', class_='auto-ellipsis').get_text(strip=True)            
            sell_link = row.find('a', href=lambda x: x and 'ContractCode=' in x)['href']
            ticker = sell_link.split('ContractCode=')[-1]            
            purchase_val = row.find('div', class_='purchase-value-cell').find('span').get_text(strip=True)
            current_val = row.find('div', class_='current-value-cell').find('span').get_text(strip=True)
            current_price = row.find('div', class_='current-price-cell').find('span').get_text(strip=True)            
            pnl_cell = row.find('div', class_='pnl-cell')            
            pnl_text = pnl_cell.get_text(" ", strip=True)
            holding = {
                "name": name,
                "ticker": ticker,
                "purchase_value": purchase_val,
                "current_value": current_val,
                "current_price": current_price,
                "pnl": pnl_text
            }            
            holdings_list.append(holding)            
        except AttributeError:            
            continue
    with open(f"{fn}_portfolio_latest.json","w",encoding="utf-8") as f:
        json.dump(holdings_list,f,indent=4, ensure_ascii=False)            
    return {"desc":desc,"holdings":holdings_list,"cash":cash_value}
    
if __name__=="__main__":
    url = "https://platform.easyequities.io/AccountOverview"        
    #asyncio.run(get_portfolio_data(url.strip(),True, *json.loads(EASYEQUITIES_PORTFOLIO_IDS)))
    #asyncio.run(download_statements(True))
    #asyncio.run(remove_password(f"{EASYEQUITIES_DOWNLOAD_PATH}/makro/ee-statements/unzipped/","EE*Monthly*.pdf",f"{EASYEQUITIES_DOWNLOAD_PATH}/ee-statements/deprotected/",EASYEQUITIES_ID_NUMBER))    
    #asyncio.run(get_all_contribution_values(f"{EASYEQUITIES_DOWNLOAD_PATH}/makro/ee-statements/deprotected/"))
    #asyncio.run(scan_for_capital_contributions(f"{EASYEQUITIES_DOWNLOAD_PATH}/makro/ee-statements/deprotected/"))    
    #asyncio.run(get_portfolio_total(f"{EASYEQUITIES_DOWNLOAD_PATH}/",f"ee_ALL*.json"))
    asyncio.run(parse_portfolio_files(f"{EASYEQUITIES_DOWNLOAD_PATH}/",f"ee_ALL*.json"))
    logger.info("Run completed.")