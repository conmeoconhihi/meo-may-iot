from flask import Flask, request, send_file
import google.generativeai as genai
from gtts import gTTS
import speech_recognition as sr
import os
import tempfile
import wave
import datetime
import yt_dlp 
import socket
import glob
import random 

app = Flask(__name__)

# ==========================================
# BĂNG ĐẠN 4 API KEY (ĐÃ UPDATE THEO LỆNH BÍ THƯ)
# ==========================================
API_KEYS = [
    "AIzaSyDS0jccnC8y_Dot2EhbEmfwyOhHL6Np3Ko",
    "AIzaSyApGTkKqTMqCsjbEjWjGGrqEx6yJeIqf9Y", # Thay thế key cũ
    "AIzaSyAmNnEDdqtGJcm5sAfpduo3fJERRzkDljw", # Key mới thêm
    "AIzaSyAAJZ2q76mJM3iS3wxMKutc44h7y6e5SFE"
]

last_mp3_path = None

def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

MY_IP = get_my_ip()

def download_soundcloud_audio(query):
    print(f"[🎵] Đang tìm bài hát: {query} trên SoundCloud...")
    
    for f in glob.glob("music_cache.*"):
        try: os.remove(f)
        except: pass

    ydl_opts = {
        'format': 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio',
        'outtmpl': 'music_cache.%(ext)s', 
        'quiet': True,
        'noplaylist': True,
        'default_search': 'scsearch1', 
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"scsearch1:{query}", download=True)
            ext = info.get('ext', 'mp3') 
            return ext
    except Exception as e:
        print(f"[❌] Lỗi tải nhạc SoundCloud: {e}")
        return None

@app.route('/')
def home():
    return "MÁY CHỦ MÈO MÁY ĐÃ SẴN SÀNG 🚀", 200

@app.route('/play_music.<ext>', methods=['GET'])
def play_music(ext):
    file_path = f"music_cache.{ext}"
    if os.path.exists(file_path):
        print(f"[▶️] Đang bơm nhạc file .{ext} xuống Mèo Máy...")
        mime = "audio/mp4" if ext in ["m4a", "mp4"] else "audio/mpeg"
        return send_file(file_path, mimetype=mime)
    return "Not found", 404

@app.route('/upload_and_ask', methods=['POST', 'GET'])
def upload_and_ask():
    global last_mp3_path
    
    if request.method == 'GET':
        if last_mp3_path and os.path.exists(last_mp3_path):
            return send_file(last_mp3_path, mimetype="audio/mpeg")
        return "Empty", 404

    audio_data = request.data
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_in:
        with wave.open(temp_in, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(audio_data)
        temp_wav_path = temp_in.name

    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav_path) as source:
            audio_record = recognizer.record(source)
            try:
                question = recognizer.recognize_google(audio_record, language="vi-VN")
                print(f"[🗣️ Bạn nói] {question}")
            except:
                question = "Nghe không rõ."
        os.remove(temp_wav_path)

        music_keywords = ["mở bài", "hát bài", "nghe nhạc", "phát bài", "play"]
        if any(word in question.lower() for word in music_keywords):
            for word in music_keywords:
                question = question.lower().replace(word, "").strip()

            banned_words = [" của ", " do ", " ca sĩ ", " band "]
            for b_word in banned_words:
                question = question.replace(b_word, " ")
            question = " ".join(question.split())

            ext = download_soundcloud_audio(question)
            if ext:
                print(f"[✅] Đã tải xong file .{ext}! Báo cho ESP32 tới lấy.")
                host_url = request.host_url 
                return f"URL:{host_url}play_music.{ext}", 200
            else:
                answer = "Tôi không tải được bài hát này."
                tts = gTTS(answer, lang='vi')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_out:
                    tts.write_to_fp(temp_out)
                    last_mp3_path = temp_out.name
                return "OK", 200
        else:
            now = datetime.datetime.now()
            
            if "kể chuyện" in question.lower() or "kể tích" in question.lower():
                mode_text = "soạn truyện"
                prompt = f"Bạn là một chú mèo máy dễ thương. Hãy kể một câu chuyện cổ tích hoặc ngụ ngôn ngắn gọn, vui nhộn (khoảng 80-100 chữ) cho bé nghe với chủ đề: {question}"
            else:
                mode_text = "trả lời thường"
                prompt = f"Bạn là mèo máy. Hôm nay là {now.strftime('%H:%M %d/%m/%Y')}. Trả lời ngắn dưới 15 chữ: {question}"
                
            answer = "Bí thư ơi em đang đuối sức, đợi em một phút rồi hỏi lại nha!"
            
            # 🔥 VÒNG LẶP SĂN API 
            keys_to_try = API_KEYS.copy()
            random.shuffle(keys_to_try) 
            
            for key in keys_to_try:
                try:
                    print(f"[🤖] Đang thử Key đuôi ...{key[-4:]} để {mode_text}...")
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(prompt)
                    answer = response.text.replace("*", "").strip()
                    
                    print(f"[✅] Xài Key ...{key[-4:]} thành công!")
                    print(f"[🤖 Mèo đáp] {answer}")
                    break 
                    
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "quota" in error_str.lower():
                        print(f"[⚠️] Key ...{key[-4:]} hết đạn (Lỗi 429). Đang nạp Key khác...")
                        continue
                    else:
                        print(f"[❌] Lỗi API bí ẩn với Key ...{key[-4:]}: {e}")
                        continue

            tts = gTTS(answer, lang='vi')
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_out:
                tts.write_to_fp(temp_out)
                last_mp3_path = temp_out.name
            return "OK", 200
        
    except Exception as e:
        print(f"[❌ Lỗi Server] {e}")
        return "Error", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print("="*40)
    print(f"🔥 MÁY CHỦ NÃO BỘ ĐÃ KHỞI ĐỘNG 🔥")
    print(f"👉 IP Máy Chủ (Test Local): {MY_IP}:{port}")
    print("="*40)
    app.run(host='0.0.0.0', port=port)