import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from gtts import gTTS

# Render पर ffmpeg को ऑटो-कॉन्फ़िगर करने के लिए
import imageio_ffmpeg
os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()

from moviepy.editor import TextClip, AudioFileClip, ColorClip, CompositeVideoClip

app = FastAPI()

# CORS अनुमति - ताकि किसी भी ब्राउज़र से रिक्वेस्ट आ सके
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    script: str

# 1. रूट URL पर आपकी index.html फ़ाइल को लोड करना
@app.get("/", response_class=HTMLResponse)
async def serve_home():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html फ़ाइल नहीं मिली! कृपया इसे GitHub पर अपलोड करें।</h1>"

# 2. वीडियो जनरेट करने का API एंडपॉइंट
@app.post("/generate-video")
async def generate_video(req: VideoRequest):
    try:
        audio_path = "/tmp/voiceover.mp3"
        output_path = "/tmp/output_ad.mp4"

        # Text-to-Speech (gTTS - हिंदी)
        tts = gTTS(text=req.script, lang="hi")
        tts.save(audio_path)
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 1080x1920 HD Vertical Canvas (Reel Style)
        bg_clip = ColorClip(size=(1080, 1920), color=[15, 23, 42], duration=duration)
        
        # स्क्रीन पर ऑन-स्क्रीन स्क्रिप्ट टेक्स्ट
        txt_clip = TextClip(
            req.script, 
            fontsize=40, 
            color='white', 
            size=(900, None), 
            method='caption'
        ).set_position('center').set_duration(duration)
        
        # ऑडियो और वीडियो को मर्ज करना
        video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(audio_clip)
        video.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast"
        )
        
        audio_clip.close()
        video.close()
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        return {"status": "success", "video_url": "/download-video"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. जनरेट हुए वीडियो को डाउनलोड/प्ले कराने का एंडपॉइंट
@app.get("/download-video")
async def download_video():
    return FileResponse("/tmp/output_ad.mp4", media_type="video/mp4", filename="EstateX_Ad.mp4")
    
