import base64
import os
from flask import Flask
from pymongo import MongoClient

# Flask App शुरू करें
app = Flask(__name__)

# MongoDB Connection
MONGO_URI = "mongodb+srv://pawandevprasad03112010_db_user:12345@firstmongodb.p4sqrf.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)

db = client["your_db_name"]  # 'your_db_name' को अपने सही DB नाम से बदलें
collection = db["your_collection_name"]  # 'your_collection_name' बदलें

os.makedirs("saved_video_frames", exist_ok=True)


@app.route("/")
def run_script():
    documents = collection.find()
    count = 0
    for doc in documents:
        image_data = doc.get("image_data")
        if image_data:
            try:
                header, encoded = image_data.split(",", 1)
                binary_data = base64.b64decode(encoded)

                filename = f"saved_video_frames/frame_{count}.jpg"
                with open(filename, "wb") as f:
                    f.write(binary_data)
                count += 1
            except Exception as e:
                print(f"Error: {e}")

    return f"Done! Saved {count} frames successfully."


# Render Port हैंडलिंग
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
  
