import os
import boto3
from decimal import Decimal
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

app = FastAPI(title="Only Broker Real Estate Portal")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))

# AWS और DynamoDB क्रेडेंशियल्स
AWS_ACCESS_KEY_ID = "AKIA32VVAONMQV5QKNED"
AWS_SECRET_ACCESS_KEY = "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"
REGION = "ap-south-1"

TABLE_NAMES = ["BUY_PROPERTY", "LARGE_PROPERTY_LISTING"]

def get_dynamodb_resource():
    return boto3.resource(
        'dynamodb',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=REGION
    )

def decimal_to_native(obj):
    """DynamoDB के Decimal डेटा को सामान्य पाइथन डेटा में बदलता है।"""
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
    """प्रॉपर्टी डेटा को सुरक्षित रूप से मानक (standardize) करता है।"""
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
        images = ["https://property-images-estatex-1.s3.ap-south-1.amazonaws.com/photo_1790848636898_001.png"]
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

@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def home(request: Request, q: str = ""):
    try:
        listings = []
        all_locations = set()
        total_db_count = 0
        query_lower = q.strip().lower()

        # जब यूजर सर्च करेगा, केवल तभी डेटाबेस स्कैन होगा
        if query_lower:
            dynamodb = get_dynamodb_resource()
            for table_name in TABLE_NAMES:
                try:
                    table = dynamodb.Table(table_name)
                    response = table.scan()
                    items = response.get('Items', [])
                    
                    while 'LastEvaluatedKey' in response:
                        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                        items.extend(response.get('Items', []))

                    for raw_item in items:
                        total_db_count += 1
                        try:
                            item = standardize_item(table_name, raw_item)
                            all_locations.add(item['search_location'])

                            if query_lower in item['search_location'].lower() or query_lower in item['unified_title'].lower():
                                listings.append(item)
                        except Exception:
                            continue
                except Exception as e:
                    print(f"Error scanning table {table_name}: {e}")

        # सीधे Jinja2 Environment का उपयोग करके HTML रेंडर करना (बिना किसी Starlette Cache एरर के)
        template = env.get_template("index.html")
        html_content = template.render(
            request=request,
            listings=listings,
            total_count=total_db_count if query_lower else 0,
            filtered_count=len(listings),
            locations=sorted(list(all_locations)),
            query=q or ""
        )
        return HTMLResponse(content=html_content)

    except Exception as e:
        return HTMLResponse(f"<h3>Internal Server Error: {str(e)}</h3>", status_code=500)

@app.get("/property/{unified_id}", response_class=HTMLResponse)
@app.head("/property/{unified_id}", response_class=HTMLResponse)
async def property_detail(request: Request, unified_id: str):
    try:
        parts = unified_id.split("_", 1)
        if len(parts) != 2:
            return HTMLResponse("<h3>Property not found</h3>", status_code=404)
        
        table_name, prop_id = parts[0], parts[1]
        if table_name not in TABLE_NAMES:
            return HTMLResponse("<h3>Property not found</h3>", status_code=404)

        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)

        property_item = None
        for key_name in ['property_id', 'id']:
            try:
                res = table.get_item(Key={key_name: prop_id})
                if 'Item' in res:
                    property_item = standardize_item(table_name, res['Item'])
                    break
            except Exception:
                continue

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
        
