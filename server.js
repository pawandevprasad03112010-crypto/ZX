const express = require('express');
const cors = require('cors');
const multer = require('multer');
const cloudinary = require('cloudinary').v2;

const app = express();

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));
app.use(express.static('public'));

// डायरेक्ट हार्डकोडेड क्रेडेंशियल्स
cloudinary.config({
  cloud_name: 'pfmjg7ip',
  api_key: '368463435529631',
  api_secret: '6u7lnfIRo4ikkXSR_GM2ziUtStM'
});

const storage = multer.memoryStorage();
const upload = multer({ 
  storage: storage,
  limits: { fileSize: 20 * 1024 * 1024 }
});

app.post('/api/upload-multiple', upload.array('images'), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ success: false, error: 'No image files provided' });
    }

    const uploadPromises = req.files.map((file) => {
      return new Promise((resolve, reject) => {
        const fileBase64 = `data:${file.mimetype};base64,${file.buffer.toString('base64')}`;
        cloudinary.uploader.upload(fileBase64, { folder: 'processed_images' }, (error, result) => {
          if (error) reject(error);
          else resolve(result.secure_url);
        });
      });
    });

    const urls = await Promise.all(uploadPromises);
    res.json({ success: true, urls: urls });
  } catch (error) {
    console.error('Batch Upload Error:', error);
    res.status(500).json({ success: false, error: error.message || 'Server Upload Failed' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
