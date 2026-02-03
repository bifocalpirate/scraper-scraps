import requests
from bs4 import BeautifulSoup
from scraper_lib import get_headers_dictionary
import datetime
import time
def get_specials(url:str,runner:str="manual"):    
    results =[]
    c = requests.get(url, headers = get_headers_dictionary("headers_1up.txt"))
    c.raise_for_status()
    doc = BeautifulSoup(c.content,"html.parser")    
    divs = doc.find_all("div",class_="product-thumb")
    for div in divs:
        prices = div.find_all("span",class_="price-normal")       
        product_name = div.find("div",class_="description").text
        product_id = div.find("input",{'name':"product_id"})['value']
        results.append({"product_id":product_id, "product_name":product_name,"price":prices[0].text})
        print(f"{product_name} - {prices[0].text} - {product_id}")        
    return {"payload":results,"source":"1up","meta":{"runner":runner, "extract_time_gmt":f"{time.asctime(time.gmtime())}"}}                     

if __name__ == "__main__":
    print(get_specials("https://1uponline.co.za/Specials-1-up"))