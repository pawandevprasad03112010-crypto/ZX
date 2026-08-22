import base64
import os
from pymongo import MongoClient

# Apni MongoDB Atlas connection string yahan daalein
MONGO_URI = "mongodb+srv://pawandevprasad03112010_db_user:12345@firstmongodb.p45qsrf.mongodb.net/?retryWrites=true&w=majority&appName=FIRSTMONGODB"

client = MongoClient(MONGO_URI)

# Aapka database aur collection name 'xxx' hai
db = client["xxx"]
collection = db["xxx"]

# Ek naya folder banega jisme saari photos save hongi
os.makedirs("saved_video_frames", exist_ok=True)

# Database se saare documents nikalna
documents = collection.find()

count = 0
for doc in documents:
  image_data = doc.get("image_data")
  if image_data:
    try:
      # Base64 header alag karke binary data banana
      header, encoded = image_data.split(",", 1)
      binary_data = base64.b64decode(encoded)

      # Har frame ko JPG image ke roop mein save karna
      filename = f"saved_video_frames/frame_{count}.jpg"
      with open(filename, "wb") as f:
        f.write(binary_data)

      print(f"Saved: {filename}")
      count += 1
    except Exception as e:
      print(f"Error decoding frame: {e}")

print(
    f"\nTotal {count} frames successfully 'saved_video_frames' folder mein"
    " download ho gaye hain!"
)

