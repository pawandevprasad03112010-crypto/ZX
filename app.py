import os
import boto3
from decimal import Decimal
from fastapi import FastAPI, Request, Query
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

    # लोकेशन फील्ड को अलग-अलग स्ट्रक्चर्स से सुरक्षित निकालना
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

@app.get("/api/locations")
async def get_locations():
    """स्वचालित रूप से सभी लोकेशंस की लिस्ट फेच करके देगा ताकि ऑटो-कंपलीट काम कर सके।"""
    dynamodb = get_dynamodb_resource()
    all_locations = set()
    for table_name in TABLE_NAMES:
        try:
            table = dynamodb.Table(table_name)
            response = table.scan(ProjectionExpression="#loc", ExpressionAttributeNames={"#loc": "location"})
            items = response.get('Items', [])
            for item in items:
                loc = item.get('location', {})
                if isinstance(loc, dict):
                    city = str(loc.get('city', ''))
                    locality = str(loc.get('locality', '') or loc.get('locality_name', '') or loc.get('society_name', ''))
                    search_loc = f"{locality}, {city}".strip(', ')
                    if search_loc:
                        all_locations.add(search_loc)
        except Exception:
            pass
    return JSONResponse(content=sorted(list(all_locations)))

@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def home(request: Request, q: str = ""):
    try:
        listings = []
        total_db_count = 0
        query_lower = q.strip().lower()

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
                            # सटीक मैचिंग लॉजिक
                            if query_lower in item['search_location'].lower() or query_lower in item['unified_title'].lower():
                                listings.append(item)
                        except Exception:
                            continue
                except Exception as e:
                    print(f"Error scanning table {table_name}: {e}")

        template = env.get_template("index.html")
        html_content = template.render(
            request=request,
            listings=listings,
            total_count=total_db_count if query_lower else 0,
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
        return HTMLResponse(f"<h3>Internal Server Error: {str(e)}</h3>", status_code.s) # Wait, status_code=500
