import os
import boto3
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# --- AWS कॉन्फ़िगरेशन ---
AWS_ACCESS_KEY_ID = "AKIA32VVAONMTGEJMYPW"
AWS_SECRET_ACCESS_KEY = "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"
REGION = "ap-south-1"
TABLE_NAME = "BUY_PROPERTY"

# AWS क्लाइंट इनिशियलाइज करें
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=REGION,
)
table = dynamodb.Table(TABLE_NAME)


def get_all_properties():
  """DynamoDB से सभी प्रॉपर्टीज फेच करता है"""
  response = table.scan()
  items = response.get("Items", [])
  while "LastEvaluatedKey" in response:
    response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
    items.extend(response.get("Items", []))
  return items


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/locations", methods=["GET"])
def get_locations():
  """डेटाबेस से सभी उपलब्ध लोकेशंस (सुझावों के लिए) की लिस्ट देता है"""
  items = get_all_properties()
  locations = set()
  for item in items:
    # आपके नेस्टेड 'location' स्ट्रक्चर के अनुसार
    loc_data = item.get("location", {})
    sub_loc = loc_data.get("sub_locality")
    city = loc_data.get("city")
    if sub_loc:
      locations.add(sub_loc)
    if city:
      locations.add(city)
  return jsonify(sorted(list(locations)))


@app.route("/api/search", methods=["GET"])
def search_properties():
  """चुनी गई लोकेशन के आधार पर लिस्टिंग्स रिटर्न करता है"""
  query = request.args.get("q", "").strip().lower()
  items = get_all_properties()
  matched_items = []

  for item in items:
    loc_data = item.get("location", {})
    sub_loc = str(loc_data.get("sub_locality", "")).lower()
    city = str(loc_data.get("city", "")).lower()

    if query in sub_loc or query in city:
      matched_items.append(item)

  return jsonify(matched_items)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
