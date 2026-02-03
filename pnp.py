#!/usr/bin/env python3
import requests
import json
import time
from scraper_lib import get_headers_dictionary

JSON_FILE = "items.json"
SLEEP_DELAY = 2

def get_component_ids():    
    cms_url = (
        "https://www.pnp.co.za/pnphybris/v2/pnp-spa/cms/pages"
        "?pageLabelOrId=homepage"
        "&fields=DEFAULT"
    )
    try:        
        response = requests.get(cms_url, headers=get_headers_dictionary("headers_pnp.txt"), timeout=10)
        response.raise_for_status()            
        page_data = response.json()        
        component_ids = []                
        if 'contentSlots' in page_data and 'contentSlot' in page_data['contentSlots']:
            slots = page_data['contentSlots']['contentSlot']
            
            for slot in slots:                
                components = slot.get('components', {}).get('component', [])                
                for component in components:     
                    title = component.get('title',None)               
                    uid = component.get('uid')
                    type_code = component.get('typeCode')                                        
                    if uid and type_code=="ProductCarouselComponent" and title is not None:
                        component_ids.append({"uid":uid, "type_code":type_code,"title":title})                
        return component_ids            
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

def get_pnp_items_by_store(store_code,*component_ids):    
    all_results = {}
    results = []
    for component_item in component_ids:        
        url = f"https://www.pnp.co.za/pnphybris/v2/pnp-spa/carousel/anonymous?pageId=homepage&componentId={component_item["uid"]}&storeCode={store_code}&productCode=&cartId=&fields=componentId,products(code,name,onlineSalesAdId,onlineSalesExtendedAdId,brandSellerId,summary,price(FULL),images(FULL),stock(FULL),potentialPromotions(DEFAULT),averageRating,numberOfReviews,variantOptions,maxOrderQuantity,categories(FULL),productDisplayBadges(DEFAULT),allowedQuantities(DEFAULT),available,quantityType,defaultQuantityOfUom,defaultUnitOfMeasure,averageWeight,strategyId),resultId&lang=en&curr=ZAR"            
        c =requests.get(url,headers=get_headers_dictionary("headers_pnp.txt"))
        time.sleep(SLEEP_DELAY)
        c.raise_for_status()
        items = json.loads(c.text.replace("\\n"," "))      
        if "products" in items:
            for item in items["products"]:
                name = item["name"]
                price = item["price"]["value"]
                available = item["available"]
                code = item["code"]
                old_price = item["price"]["oldPrice"]
                old_price = f"{old_price}" if old_price else price
                special_price =  item["potentialPromotions"][0]["promotionTextMessage"] if "potentialPromotions" in item else None
                if available:
                    if not special_price:            
                        results.append({"name":name,"price":price,"old_price":old_price,"available":available,"code":code})
                    else:
                        results.append({"name":name,"price":special_price,"old_price":price,"available":available,"code":code})        
                    print(f"{name} ({special_price if special_price else price})" )            
            all_results[component_item["title"]] = results            
    with open(f"{store_code}_{JSON_FILE}","w",encoding="utf-8") as f:
        json.dump(all_results,f,indent=4, ensure_ascii=False)            
    return all_results

component_ids = get_component_ids()
[print(f"{x['title']}-{x['uid']}") for x in component_ids]
items_on_promotion = get_pnp_items_by_store("WC42",*component_ids) #plattekloof