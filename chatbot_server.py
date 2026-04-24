from flask import Flask, request, send_file
import google.generativeai as genai
from gtts import gTTS
import speech_recognition as sr
import os
import yt_dlp 
import socket
import glob
import random 
import traceback

app = Flask(__name__)

# ==========================================
# 🔐 THUẬT TOÁN KÉT SẮT: LẤY API KEY AN TOÀN
# ==========================================
# Khi chạy Cloud: Nó sẽ tự lấy danh sách Key từ Két sắt của Render
# Khi chạy Laptop: Nó sẽ xài tạm cái Key dự phòng ở dưới (Tui đã nhét 1 Key mới của m vào để test)
raw_keys = os.environ.get("GEMINI_KEYS", "")
API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]

# Đặt tên file cố định chống mất trí nhớ cho Cloud
ANSWER_FILE = "answer_cache.mp3"
INPUT_WAV = "input_cache.wav"

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
    print(f"[🎵] Đang tìm bài hát/Mix: {query} trên SoundCloud...")
    for f in glob.glob("music_cache.*"):
        try: os.remove(f)
        except: pass

    ydl_opts = {
        'format': 'bestaudio/best', 
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
        print(f"[❌] Lỗi tải nhạc: {e}")
        return None

@app.route('/')
def home():
    return "MÁY CHỦ MÈO MÁY ĐÃ BẢO MẬT THÀNH CÔNG 🚀🔐", 200

@app.route('/play_music.<ext>', methods=['GET'])
def play_music(ext):
    file_path = f"music_cache.{ext}"
    if os.path.exists(file_path):
        mime = "audio/mp4" if ext in ["m4a", "mp4"] else "audio/mpeg"
        return send_file(file_path, mimetype=mime)
    return "Not found", 404

@app.route('/upload_and_ask', methods=['POST', 'GET'])
def upload_and_ask():
    if request.method == 'GET':
        if os.path.exists(ANSWER_FILE):
            return send_file(ANSWER_FILE, mimetype="audio/mpeg")
        return "Empty", 404

    audio_data = request.data
    with open(INPUT_WAV, 'wb') as wav_file:
        wav_file.write(audio_data)

    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(INPUT_WAV) as source:
            audio_record = recognizer.record(source)
            try:
                question = recognizer.recognize_google(audio_record, language="vi-VN")
                print(f"[🗣️ Bạn nói] {question}")
            except:
                question = "Nghe không rõ."

        music_keywords = ["mở bài", "hát bài", "nghe nhạc", "phát bài", "play", "mở playlist", "mở mix"]
        if any(word in question.lower() for word in music_keywords):
            
            is_long_mix = False
            if "playlist" in question.lower() or "mix" in question.lower() or "tuyển tập" in question.lower():
                is_long_mix = True

            for word in music_keywords:
                question = question.lower().replace(word, "").strip()

            search_query = question
            if is_long_mix:
                search_query = f"{question} mix" 
                print(f"[🎧] Đang cày cuốc Playlist/Mix: '{search_query}'...")

            ext = download_soundcloud_audio(search_query)
            if ext:
                print(f"[✅] Đã tải xong nhạc! Báo Mèo tới lấy.")
                host_url = request.host_url 
                return f"URL:{host_url}play_music.{ext}", 200
            else:
                answer = "Tải nhạc thất bại, có thể bài này quá nặng."
                try:
                    tts = gTTS(answer, lang='vi')
                    tts.save(ANSWER_FILE)
                except: pass
                return "OK", 200
        else:
            now = datetime.datetime.now()
            
            if "kể chuyện" in question.lower() or "kể tích" in question.lower():
                mode_text = "soạn truyện"
                prompt = f"Bạn là mèo máy. Kể một chuyện cổ tích cực ngắn, vui (khoảng 60 chữ) chủ đề: {question}"
            else:
                mode_text = "trả lời thường"
                prompt = f"Bạn là mèo máy. Hôm nay là {now.strftime('%H:%M %d/%m/%Y')}. Trả lời cực ngắn dưới 15 chữ: {question}"
                
            answer = "Bí thư ơi mạng đang lag, chờ em xíu nha!"
            
            keys_to_try = API_KEYS.copy()
            random.shuffle(keys_to_try) 
            
            for key in keys_to_try:
                try:
                    print(f"[🤖] Đang xài Key ...{key[-4:]} để {mode_text}...")
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(prompt)
                    answer = response.text.replace("*", "").strip()
                    print(f"[🤖 Mèo đáp] {answer}")
                    break 
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        continue
                    elif "403" in str(e):
                        print(f"[❌] Key ...{key[-4:]} đã bị Google khóa!")
                        continue
                    else: continue

            try:
                tts = gTTS(answer, lang='vi')
                tts.save(ANSWER_FILE)
            except Exception as e:
                print(f"[❌] Lỗi tạo giọng đọc: {e}")
                
            return "OK", 200
        
    except Exception as e:
        print(f"[❌ LỖI FATAL] {traceback.format_exc()}")
        return "Error", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print("="*40)
    print(f"🔥 MÁY CHỦ NÃO BỘ ĐÃ KHỞI ĐỘNG 🔥")
    print(f"👉 IP Test Local: {MY_IP}:{port}")
    print("="*40)
    app.run(host='0.0.0.0', port=port)
