import os
import boto3
from decimal import Decimal
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader

app = FastAPI(title="Only Broker Real Estate Portal")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))

# AWS और DynamoDB क्रेडेंशियल्स
AWS_ACCESS_KEY_ID = "AKIA32VVAONMQV5QKNED"
AWS_SECRET_ACCESS_KEY = "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"
REGION = "ap-south-1"

TABLE_NAMES = ["BUY_PROPERTY", "LARGE_PROPERTY_LISTING"]

# ग्लोबल कैश
_GLOBAL_CACHE = {
    "listings": [],
    "locations": [],
    "loaded": False
}

def get_dynamodb_resource():
    return boto3.resource(
        'dynamodb',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=REGION
    )

def decimal_to_native(obj):
    if isinstance(obj, list):
        return [decimal_to_native(i) for i in obj]
    elif isinstance(obj, dict):
        return {str(k): decimal_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    return obj

def standardize_item(table_name, raw_item):
    item = decimal_to_native(raw_item)
    prop_id = str(item.get('property_id') or item.get('id') or item.get('_id') or 'unknown')
    item['unified_id'] = f"{table_name}_{prop_id}"
    item['source_table'] = table_name

    # लोकेशन
    loc = item.get('location', {})
    city, locality = "", ""
    if isinstance(loc, dict):
        city = str(loc.get('city', ''))
        locality = str(loc.get('locality', '') or loc.get('locality_name', '') or loc.get('society_name', ''))
    else:
        city = str(item.get('city', ''))
        locality = str(item.get('locality', ''))
    
    search_loc = f"{locality}, {city}".strip(', ')
    item['search_location'] = search_loc if search_loc else "Unknown Location"

    # इमेजेस
    images = []
    media = item.get('media', {})
    if isinstance(media, dict):
        img_list = media.get('images', [])
        if isinstance(img_list, list):
            images = [str(img) for img in img_list if img and str(img).startswith('http')]
    
    if not images:
        images = [""]
    item['unified_images'] = images

    # टाइटल और प्राइस
    listing_sec = item.get('listing', {})
    entity_sec = item.get('entity', {})
    pricing_sec = item.get('pricing', {})

    title = str(listing_sec.get('title') or entity_sec.get('title') or item.get('title') or 'Residential Property')
    item['unified_title'] = title
    item['unified_price'] = str(pricing_sec.get('display_price') or pricing_sec.get('price_in_words') or item.get('price') or 'Contact for Price')
    
    prop_sec = item.get('property', {})
    item['unified_bhk'] = str(prop_sec.get('bedrooms') or item.get('bedrooms') or '2')
    
    area_sec = prop_sec.get('area', {})
    if isinstance(area_sec, dict):
        item['unified_area'] = str(area_sec.get('display_area') or item.get('area') or 'Standard Area')
    else:
        item['unified_area'] = str(item.get('area') or 'Standard Area')

    return item

def load_data_lazily():
    """सेफ तरीके से डेटा लोड करता है ताकि टाइमआउट न हो।"""
    if _GLOBAL_CACHE["loaded"]:
        return

    dynamodb = get_dynamodb_resource()
    all_items = []
    all_locations = set()

    for table_name in TABLE_NAMES:
        try:
            table = dynamodb.Table(table_name)
            response = table.scan()
            items = response.get('Items', [])
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))

            for raw_item in items:
                try:
                    item = standardize_item(table_name, raw_item)
                    all_items.append(item)
                    if item['search_location'] != "Unknown Location":
                        all_locations.add(item['search_location'])
                except Exception:
                    continue
        except Exception as e:
            print(f"Error loading table {table_name}: {e}")

    _GLOBAL_CACHE["listings"] = all_items
    _GLOBAL_CACHE["locations"] = sorted(list(all_locations))
    _GLOBAL_CACHE["loaded"] = True

@app.get("/api/locations")
async def get_locations():
    load_data_lazily()
    return JSONResponse(content=_GLOBAL_CACHE["locations"])

@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def home(request: Request, q: str = ""):
    try:
        # जैसे ही यूजर आएगा, डेटा सुरक्षित रूप से लोड हो जाएगा
        load_data_lazily()
        
        listings = []
        query_lower = q.strip().lower()
        all_listings = _GLOBAL_CACHE["listings"]

        if query_lower:
            listings = [
                item for item in all_listings
                if query_lower in item['search_location'].lower() or query_lower in item['unified_title'].lower()
            ]

        template = env.get_template("index.html")
        html_content = template.render(
            request=request,
            listings=listings,
            total_count=len(all_listings),
            filtered_count=len(listings),
            query=q or ""
        )
        return HTMLResponse(content=html_content)

    except Exception as e:
        return HTMLResponse(f"<h3>Internal Server Error: {str(e)}</h3>", status_code=500)

@app.get("/property/{unified_id}", response_class=HTMLResponse)
@app.head("/property/{unified_id}", response_class=HTMLResponse)
async def property_detail(request: Request, unified_id: str):
    try:
        load_data_lazily()
        property_item = next((item for item in _GLOBAL_CACHE["listings"] if item['unified_id'] == unified_id), None)

        if not property_item:
            return HTMLResponse("<h3>Property not found</h3>", status_code=404)

        template = env.get_template("detail.html")
        html_content = template.render(
            request=request,
            property=property_item
        )
        return HTMLResponse(content=html_content)

    except Exception as e:
        return HTMLResponse(f"<h3>Internal Server Error: {str(e)}</h3>", status_code=500)
        
