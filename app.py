import os
import boto3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Only Broker Real Estate Portal")

# सही पाथ के साथ टेम्पलेट्स सेट करना
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

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

def search_listings_on_demand(query_str: str = ""):
    dynamodb = get_dynamodb_resource()
    matched_listings = []
    all_locations = set()
    total_db_count = 0

    query_lower = query_str.strip().lower()

    for table_name in TABLE_NAMES:
        try:
            table = dynamodb.Table(table_name)
            response = table.scan()
            items = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))

            for item in items:
                total_db_count += 1
                try:
                    prop_id = str(item.get('property_id') or item.get('id') or item.get('_id') or 'unknown')
                    item['unified_id'] = f"{table_name}_{prop_id}"
                    item['source_table'] = table_name

                    # लोकेशन स्टैंडर्डाइज़ेशन
                    loc = item.get('location', {})
                    city, locality = "", ""
                    if isinstance(loc, dict):
                        city = str(loc.get('city', ''))
                        locality = str(loc.get('locality', '') or loc.get('locality_name', '') or loc.get('society_name', ''))
                    else:
                        city = str(item.get('city', ''))
                        locality = str(item.get('locality', ''))
                    
                    search_loc = f"{locality}, {city}".strip(', ')
                    if not search_loc:
                        search_loc = "Unknown Location"
                    
                    item['search_location'] = search_loc
                    all_locations.add(search_loc)

                    # इमेजेस स्टैंडर्डाइज़ेशन
                    images = []
                    media = item.get('media', {})
                    if isinstance(media, dict):
                        img_list = media.get('images', [])
                        if isinstance(img_list, list):
                            images = [str(img) for img in img_list if img and str(img).startswith('http')]
                    
                    if not images:
                        images = ["https://property-images-estatex-1.s3.ap-south-1.amazonaws.com/photo_1790848636898_001.png"]
                    
                    item['unified_images'] = images

                    # टाइटल और प्राइस स्टैंडर्डाइज़ेशन
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

                    if not query_lower or (query_lower in search_loc.lower() or query_lower in title.lower()):
                        matched_listings.append(item)

                except Exception:
                    continue

        except Exception as e:
            print(f"Error scanning table {table_name}: {e}")

    return matched_listings, sorted(list(all_locations)), total_db_count

@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def home(request: Request, q: str = ""):
    listings, locations, total_count = search_listings_on_demand(q)

    # सुरक्षित और सही TemplateResponse सिंटैक्स
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "listings": listings,
            "total_count": total_count,
            "filtered_count": len(listings),
            "locations": locations,
            "query": q or ""
        }
    )

@app.get("/property/{unified_id}", response_class=HTMLResponse)
@app.head("/property/{unified_id}", response_class=HTMLResponse)
async def property_detail(request: Request, unified_id: str):
    listings, _, _ = search_listings_on_demand("")
    property_item = next((item for item in listings if item['unified_id'] == unified_id), None)
    
    if not property_item:
        return HTMLResponse("<h3>Property not found</h3>", status_code=404)

    return templates.TemplateResponse(
        "detail.html", 
        {
            "request": request,
            "property": property_item
        }
    )
    
