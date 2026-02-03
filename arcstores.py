#!/usr/bin/env python3
import requests
import time
import json
SLEEP_DELAY_IN_SECONDS = 1.5
JSON_FILE = "arcstore_items.json"
def get_product_data(*args):
    result = []
    for product_id in args:
        url = f"https://www.arcstore.co.za/Default.aspx?ID=9754&ProductID={product_id}&VariantID=WEIWEI252G&Feed=True&redirect=false"
        response = requests.get(url)    
        response.raise_for_status()
        data = response.json()        
        product = data[0]
        on_sale = False
        out_of_stock = False
        image_url = None
        if product['outOfStock']:
            out_of_stock=True
        if 'StickersContainers' in product:        
            if len(product['StickersContainers']) > 0 and 'Stickers' in product['StickersContainers'][0]:            
                on_sale = product['StickersContainers'][0]['Stickers'][0]['Title'] == 'SALE'
        if (len(product['ThumbnailImages'])>0):
            image_url = f"https://www.arcstore.co.za/{product['ThumbnailImages'][0]['image']}"
        time.sleep(SLEEP_DELAY_IN_SECONDS)
        if not out_of_stock:
            result.append({
                "product_id":str(product_id),
                "name":product['name'],
                "price":product['price'],
                "out_of_stock":out_of_stock,
                "on_sale":on_sale,
                "image_url" : image_url
            })   
    with open(f"{JSON_FILE}","w",encoding="utf-8") as f:
        json.dump(result,f,indent=4, ensure_ascii=False)                 
    return result

if __name__=="__main__":
    print(get_product_data(106974,107010))