import os
import boto3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Only Broker Real Estate Portal")
templates = Jinja2Templates(directory="templates")

# AWS and DynamoDB Credentials
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

def fetch_all_listings():
    """Scans both tables and standardizes fields safely."""
    dynamodb = get_dynamodb_resource()
    all_listings = []

    for table_name in TABLE_NAMES:
        try:
            table = dynamodb.Table(table_name)
            response = table.scan()
            items = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))

            for item in items:
                try:
                    prop_id = str(item.get('property_id') or item.get('id') or item.get('_id') or 'unknown')
                    item['unified_id'] = f"{table_name}_{prop_id}"
                    item['source_table'] = table_name

                    loc = item.get('location', {})
                    city, locality = "", ""
                    if isinstance(loc, dict):
                        city = str(loc.get('city', ''))
                        locality = str(loc.get('locality', '') or loc.get('locality_name', '') or loc.get('society_name', ''))
                    else:
                        city = str(item.get('city', ''))
                        locality = str(item.get('locality', ''))
                    
                    item['search_location'] = f"{locality}, {city}".strip(', ')
                    if not item['search_location']:
                        item['search_location'] = "Unknown Location"

                    images = []
                    media = item.get('media', {})
                    if isinstance(media, dict):
                        img_list = media.get('images', [])
                        if isinstance(img_list, list):
                            images = [str(img) for img in img_list if img and str(img).startswith('http')]
                    
                    if not images:
                        images = ["https://property-images-estatex-1.s3.ap-south-1.amazonaws.com/photo_1790848636898_001.png"]
                    
                    item['unified_images'] = images

                    listing_sec = item.get('listing', {})
                    entity_sec = item.get('entity', {})
                    pricing_sec = item.get('pricing', {})

                    item['unified_title'] = str(listing_sec.get('title') or entity_sec.get('title') or item.get('title') or 'Residential Property')
                    item['unified_price'] = str(pricing_sec.get('display_price') or pricing_sec.get('price_in_words') or item.get('price') or 'Contact for Price')
                    
                    prop_sec = item.get('property', {})
                    item['unified_bhk'] = str(prop_sec.get('bedrooms') or item.get('bedrooms') or '2')
                    
                    area_sec = prop_sec.get('area', {})
                    if isinstance(area_sec, dict):
                        item['unified_area'] = str(area_sec.get('display_area') or item.get('area') or 'Standard Area')
                    else:
                        item['unified_area'] = str(item.get('area') or 'Standard Area')

                    all_listings.append(item)
                except Exception as inner_ex:
                    continue

        except Exception as e:
            print(f"Error scanning table {table_name}: {e}")

    return all_listings

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, q: str = ""):
    listings = fetch_all_listings()
    total_count = len(listings)

    locations = sorted(list(set(item['search_location'] for item in listings if item['search_location'])))

    filtered_listings = listings
    selected_query = ""

    if q:
        selected_query = q.strip().lower()
        filtered_listings = [
            item for item in listings 
            if selected_query in item['search_location'].lower() 
            or selected_query in item['unified_title'].lower()
        ]

    # आधुनिक Starlette TemplateResponse फॉर्मेट
    return templates.TemplateResponse(
        request, 
        "index.html", 
        {
            "request": request,
            "listings": filtered_listings,
            "total_count": total_count,
            "filtered_count": len(filtered_listings),
            "locations": locations,
            "query": q or ""
        }
    )

@app.get("/property/{unified_id}", response_class=HTMLResponse)
async def property_detail(request: Request, unified_id: str):
    listings = fetch_all_listings()
    property_item = next((item for item in listings if item['unified_id'] == unified_id), None)
    
    if not property_item:
        return HTMLResponse("<h3>Property not found</h3>", status_code=404)

    return templates.TemplateResponse(
        request, 
        "detail.html", 
        {
            "request": request,
            "property": property_item
        }
    )
    
