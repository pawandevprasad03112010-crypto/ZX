import os
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from gtts import gTTS
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    script: str

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html फ़ाइल नहीं मिली!</h1>"

@app.post("/generate-video")
async def generate_video(req: VideoRequest):
    try:
        audio_path = "/tmp/voiceover.mp3"
        video_temp_path = "/tmp/temp_video.mp4"
        final_output_path = "/tmp/output_ad.mp4"

        # 1. Voiceover (gTTS)
        tts = gTTS(text=req.script, lang="hi")
        tts.save(audio_path)

        # ऑडियो की अवधि (duration) का अनुमान लगाना
        word_count = len(req.script.split())
        duration = max(5, int(word_count * 0.4))
        fps = 24
        total_frames = duration * fps

        # 2. OpenCV से 1080x1920 (Reel Video) बनाना
        height, width = 1920, 1080
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_temp_path, fourcc, fps, (width, height))

        for _ in range(total_frames):
            # डार्क ब्लू बैकग्राउंड
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:] = (42, 23, 15)  # BGR Color

            # स्क्रीन पर EstateX हेडर
            cv2.putText(frame, "EstateX App", (300, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
            cv2.putText(frame, "Buy, Rent, Sell & Service", (200, 400), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (56, 189, 248), 3)

            # ऐप फीचर्स
            cv2.putText(frame, "- 100% Verified Properties", (150, 700), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            cv2.putText(frame, "- Local Plumbers & Electricians", (150, 850), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            
            # कॉल टू एक्शन
            cv2.putText(frame, "Download Now on Google Play", (150, 1500), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (74, 222, 128), 4)

            out.write(frame)

        out.release()

        # 3. FFmpeg से ऑडियो और वीडियो मर्ज करना
        cmd = f"ffmpeg -y -i {video_temp_path} -i {audio_path} -c:v copy -c:a aac {final_output_path}"
        subprocess.run(cmd, shell=True, check=True)

        return {"status": "success", "video_url": "/download-video"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-video")
async def download_video():
    if os.path.exists("/tmp/output_ad.mp4"):
        return FileResponse("/tmp/output_ad.mp4", media_type="video/mp4", filename="EstateX_Ad.mp4")
    raise HTTPException(status_code=404, detail="वीडियो फ़ाइल नहीं मिली")
    
