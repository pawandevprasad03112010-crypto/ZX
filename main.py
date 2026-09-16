import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gtts import gTTS

# Render पर ffmpeg की राह आसान करने के लिए ऑटो-कॉन्फ़िगरेशन
import imageio_ffmpeg
os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()

from moviepy.editor import TextClip, AudioFileClip, ColorClip, CompositeVideoClip

app = FastAPI()

# CORS अनुमति - ताकि किसी भी वेबसाइट/HTML से रिक्वेस्ट आ सके
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
    return {"status": "EstateX Video Generator API is Online and Active!"}

@app.post("/generate-video")
async def generate_video(req: VideoRequest):
    try:
        # Render के फ्री कंटेनर के लिए अस्थायी फ़ाइल पाथ (/tmp फ़ोल्डर)
        audio_path = "/tmp/voiceover.mp3"
        output_path = "/tmp/output_ad.mp4"

        # 1. Text-to-Speech (gTTS - हिंदी आवाज़)
        tts = gTTS(text=req.script, lang="hi")
        tts.save(audio_path)
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 2. HD Vertical Reel Aspect Ratio (1080x1920)
        bg_clip = ColorClip(size=(1080, 1920), color=[15, 23, 42], duration=duration)
        
        # 3. On-Screen Caption Text
        txt_clip = TextClip(
            req.script, 
            fontsize=40, 
            color='white', 
            size=(900, None), 
            method='caption'
        ).set_position('center').set_duration(duration)
        
        # 4. Composite Audio & Video
        video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(audio_clip)
        video.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast"  # तेज रेंडरिंग के लिए
        )
        
        # क्लोज करके मेमोरी साफ़ करें
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
    
