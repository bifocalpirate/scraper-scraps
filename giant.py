import requests
import pdfplumber
import json
import re

# The direct URL you discovered
# pdf_url = "https://cdnc.heyzine.com/files/uploaded/v3/e260d8c297a063c5e8f6e69eee983687ff759478.pdf"
pdf_filename = "giant_hyper_specials.pdf"
json_output = "giant_hyper_specials.json"

def download_pdf(url, filename):
    print(f"Downloading PDF from {url}...")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
        return True
    else:
        print(f"Failed to download. Status code: {response.status_code}")
        return False

def extract_products(pdf_path):
    products = []
    # Regex to find prices (e.g., R49.99, 49.99, R 49 99)
    # This is a general pattern; you might need to tweak based on the PDF's specific layout
    price_pattern = re.compile(r'R\s?(\d+[\.,]\d{2}|\d+)')
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Processing {len(pdf.pages)} pages...")
        for i, page in enumerate(pdf.pages):
            # Extract text
            text = page.extract_text()
            print(text)
            if not text:
                continue
            
            # Simple line-by-line parsing strategy
            # (Leaflets are often grid-based, so this splits text by newlines)
            lines = text.split('\n')
            
            for line in lines:
                # Look for lines containing a price
                price_match = price_pattern.search(line)
                if price_match:
                    price = price_match.group(0)
                    # Assumes product name is the text before the price
                    # You might need to adjust logic if price comes first or if text is wrapped
                    parts = line.split(price)
                    name = parts[0].strip()
                    unit_info = parts[1].strip() if len(parts) > 1 else ""
                    
                    # Clean up common noise
                    if len(name) > 3: 
                        products.append({
                            "product_name": name,
                            "price": price,
                            "unit": unit_info,
                            "page": i + 1
                        })
    return products

data = extract_products(pdf_filename)
    
with open(json_output, 'w') as f:
    json.dump(data, f, indent=4)
    
print(f"Successfully extracted {len(data)} items to {json_output}")