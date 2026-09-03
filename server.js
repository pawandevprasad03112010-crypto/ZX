const express = require('express');
const cors = require('cors');
const multer = require('multer');
const cloudinary = require('cloudinary').v2;

const app = express();

app.use(cors());

// बड़ी फाइलों के लिए लिमिट बढ़ा दी गई है
app.use(express.json({ limit: '100mb' }));
app.use(express.urlencoded({ limit: '100mb', extended: true }));
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
  limits: { fileSize: 50 * 1024 * 1024 } // 50MB per file limit
});

app.post('/api/upload-multiple', upload.array('images'), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ success: false, error: 'No image files provided' });
    }

    // सीरियल ऑर्डर बनाए रखने के लिए Sequentially अपलोड करना (Render timeout से बचने के लिए)
    const urls = [];
    for (const file of req.files) {
      const result = await new Promise((resolve, reject) => {
        const stream = cloudinary.uploader.upload_stream(
          { folder: 'processed_images', resource_type: 'image' },
          (error, result) => {
            if (error) reject(error);
            else resolve(result);
          }
        );
        stream.end(file.buffer);
      });
      urls.push(result.secure_url);
    }

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
  
