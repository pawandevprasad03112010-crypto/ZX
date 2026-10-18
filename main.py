import os
import uuid
import json
import boto3
from decimal import Decimal
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# AWS & DynamoDB Configuration
AWS_ACCESS_KEY_ID = "AKIA32VVAONMQV5QKNED"
AWS_SECRET_ACCESS_KEY = "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"
REGION = "ap-south-1"
TABLE_NAME = "LARGE_PROPERTY_LISTING"
PRIMARY_KEY = "property_id"

dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=REGION
)
table = dynamodb.Table(TABLE_NAME)

# Helper function: Python float/int ko DynamoDB Decimal mein convert karne ke liye
def convert_floats_to_decimals(obj):
    if isinstance(obj, list):
        return [convert_floats_to_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, int):
        return Decimal(str(obj))
    return obj

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ONLY BROKER - DynamoDB Insert</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 850px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h2 { color: #2c3e50; text-align: center; margin-bottom: 5px; }
        p.subtitle { text-align: center; color: #7f8c8d; font-size: 14px; margin-bottom: 20px; }
        textarea { width: 100%; height: 280px; padding: 12px; border: 1px solid #ccc; border-radius: 8px; font-size: 13px; font-family: monospace; box-sizing: border-box; resize: vertical; background: #fafafa; }
        .btn-submit { background: #27ae60; color: white; border: none; padding: 14px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; margin-top: 15px; font-weight: bold; transition: background 0.2s; }
        .btn-submit:hover { background: #219653; }
        .loader { text-align: center; display: none; margin-top: 15px; font-weight: bold; color: #e67e22; }
        
        .result-card { margin-top: 25px; padding: 20px; background: #e8f8f5; border: 1px solid #a3e4d7; border-radius: 8px; display: none; text-align: center; }
        .result-card h3 { color: #16a085; margin-top: 0; }
        .property-id-box { background: #2c3e50; color: #f1c40f; padding: 12px; font-size: 18px; font-family: monospace; border-radius: 6px; font-weight: bold; letter-spacing: 1px; word-break: break-all; display: inline-block; margin: 10px 0; }
        .btn-copy { background: #3498db; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; margin-left: 10px; }
        .btn-copy:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div class="container">
        <h2>ONLY BROKER</h2>
        <p class="subtitle">Table: <b>LARGE_PROPERTY_LISTING</b> mein JSON Entry Karein</p>
        
        <textarea id="jsonInput" placeholder='{\n  "title_and_description": {\n    "title": "3 BHK Flat for sale"\n  },\n  "pricing": {\n    "price_numeric": 14500000\n  }\n}'></textarea>
        
        <button class="btn-submit" onclick="submitToDynamoDB()">Submit to DynamoDB</button>
        <div class="loader" id="loader">⏳ DynamoDB mein save ho raha hai, kripya intezaar karein...</div>

        <div class="result-card" id="resultCard">
            <h3>🎉 Listing Successfully Saved!</h3>
            <p>Aapki Property ID niche hai:</p>
            <div id="propertyIdDisplay" class="property-id-box"></div>
            <button class="btn-copy" onclick="copyPropertyId()">Copy ID</button>
        </div>
    </div>

    <script>
        async function submitToDynamoDB() {
            let jsonText = document.getElementById("jsonInput").value.trim();
            if(!jsonText) {
                alert("Kripya kuch JSON data daalein!");
                return;
            }

            try {
                JSON.parse(jsonText);
            } catch(e) {
                alert("Invalid JSON Format! Kripya sahi JSON syntax daalein.");
                return;
            }

            document.getElementById("loader").style.display = "block";
            document.getElementById("resultCard").style.display = "none";

            try {
                let response = await fetch('/insert_property', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ raw_json: jsonText })
                });

                let result = await response.json();
                document.getElementById("loader").style.display = "none";

                if(result.success) {
                    document.getElementById("propertyIdDisplay").innerText = result.property_id;
                    document.getElementById("resultCard").style.display = "block";
                    document.getElementById("jsonInput").value = "";
                } else {
                    alert("Error: " + result.error);
                }
            } catch (err) {
                document.getElementById("loader").style.display = "none";
                alert("Request failed!");
            }
        }

        function copyPropertyId() {
            let propId = document.getElementById("propertyIdDisplay").innerText;
            navigator.clipboard.writeText(propId).then(() => {
                alert("Property ID copied to clipboard!");
            });
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/insert_property", methods=["POST"])
def insert_property():
    try:
        req_data = request.json
        raw_json_str = req_data.get("raw_json", "")
        
        item_dict = json.loads(raw_json_str)
        
        # Agar JSON mein property_id na ho toh automatic unique UUID bana do
        if PRIMARY_KEY not in item_dict or not item_dict[PRIMARY_KEY]:
            item_dict[PRIMARY_KEY] = str(uuid.uuid4())
            
        generated_id = item_dict[PRIMARY_KEY]
        
        item_to_save = convert_floats_to_decimals(item_dict)
        table.put_item(Item=item_to_save)
        
        return jsonify({"success": True, "property_id": generated_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    
