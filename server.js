const express = require('express');
const cors = require('cors');
const multer = require('multer');
const cloudinary = require('cloudinary').v2;
const path = require('path');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Configure Cloudinary
cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET
});

// Configure Multer (Memory Storage)
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

// Single Image Upload Endpoint
app.post('/api/upload', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, error: 'No image file provided' });
    }

    // Convert Buffer to Data URI
    const fileBase64 = `data:${req.file.mimetype};base64,${req.file.buffer.toString('base64')}`;

    // Upload directly to Cloudinary via SDK
    const result = await cloudinary.uploader.upload(fileBase64, {
      folder: 'auto_cropped_watermarked'
    });

    res.json({ success: true, url: result.secure_url });
  } catch (error) {
    console.error('Cloudinary Upload Error:', error);
    res.status(500).json({ success: false, error: error.message || 'Server Upload Failed' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});

