import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gtts import gTTS
from moviepy.editor import TextClip, AudioFileClip, ColorClip, CompositeVideoClip

app = FastAPI()

# Frontend (HTML) से रिक्वेस्ट स्वीकार करने के लिए CORS अनुमति
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    script: str

@app.get("/")
def home():
    return {"status": "EstateX Video Generator API is Online"}

@app.post("/generate-video")
async def generate_video(req: VideoRequest):
    try:
        # अस्थाई फ़ाइल पाथ (Render के लिए /tmp फोल्डर उपयोग होता है)
        audio_path = "/tmp/voiceover.mp3"
        output_path = "/tmp/output_ad.mp4"

        # 1. Text-to-Speech (gTTS से हिंदी वॉयस तैयार करना)
        tts = gTTS(text=req.script, lang="hi")
        tts.save(audio_path)
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 2. 9:16 वर्टिकल कैनवास (1080x1920 HD Reel Aspect Ratio)
        bg_clip = ColorClip(size=(1080, 1920), color=[15, 23, 42], duration=duration)
        
        # 3. स्क्रिप्ट ऑन-स्क्रीन टेक्स्ट (Caption style)
        txt_clip = TextClip(
            req.script, 
            fontsize=42, 
            color='white', 
            size=(900, None), 
            method='caption'
        ).set_position('center').set_duration(duration)
        
        # 4. ऑडियो और वीडियो को मर्ज (Combine) करना
        video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(audio_clip)
        video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        
        # मेमोरी खाली करने के लिए क्लिप्स बंद करना
        audio_clip.close()
        video.close()
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        return {"status": "success", "video_url": "/download-video"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-video")
async def download_video():
    return FileResponse("/tmp/output_ad.mp4", media_type="video/mp4", filename="EstateX_Ad.mp4")
          
