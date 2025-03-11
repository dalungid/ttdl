import requests
import sys
import os
import random
import json
import subprocess
import shutil
import platform

# Konfigurasi Facebook API
API_VERSION = 'v22.0'  # Versi API terbaru per 2024
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB per chunk

def check_os():
    system = platform.system().lower()
    if 'linux' in system:
        return 'termux' if 'ANDROID_ROOT' in os.environ else 'linux'
    return 'windows' if 'windows' in system else 'unknown'

def check_ffmpeg():
    if shutil.which('ffmpeg'):
        return True
    if check_os() == 'termux':
        try:
            return subprocess.run(
                ['pkg', 'list-installed', 'ffmpeg'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).returncode == 0
        except:
            pass
    return False

def get_config():
    default = {
        "text": "FB: GameBoo",
        "font_size": 24,
        "font_color": "#FFFFFF",
        "alpha": 0.7,
        "shadow_offset": 1,
        "access_token": "YOUR_TOKEN_HERE",
        "page_id": ""  # Kosongkan untuk akun pribadi
    }
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            return {
                "text": config.get("text", default["text"]),
                "font_size": config.get("font_size", default["font_size"]),
                "font_color": config.get("font_color", default["font_color"]),
                "alpha": config.get("alpha", default["alpha"]),
                "shadow_offset": config.get("shadow_offset", default["shadow_offset"]),
                "access_token": config.get("access_token", default["access_token"]),
                "page_id": config.get("page_id", default["page_id"])
            }
    except:
        return default

def upload_reels(video_path, title, description, access_token, page_id=None):
    try:
        # Step 1: Inisiasi upload
        parent_object = page_id if page_id else 'me'
        start_url = f"https://graph.facebook.com/{API_VERSION}/{parent_object}/video_reels"
        file_size = os.path.getsize(video_path)
        
        start_params = {
            'upload_phase': 'start',
            'access_token': access_token
        }
        start_response = requests.post(start_url, data=start_params)
        start_data = start_response.json()
        
        if 'video_id' not in start_data:
            return False, f"Gagal inisiasi: {start_data.get('error', {}).get('message', 'Unknown error')}"

        video_id = start_data['video_id']
        upload_url = f"https://rupload.facebook.com/video-upload/{API_VERSION}/{video_id}"
        print(f"[i] Video ID: {video_id}")

        # Step 2: Upload video
        headers = {
            'Authorization': f'OAuth {access_token}',
            'User-Agent': 'Python/ReelsUploader',
            'Content-Type': 'application/octet-stream'
        }
        
        with open(video_path, 'rb') as f:
            offset = 0
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                
                chunk_headers = {
                    'offset': str(offset),
                    'file_size': str(file_size),
                    **headers
                }
                
                response = requests.post(upload_url, headers=chunk_headers, data=chunk)
                
                if response.status_code != 200:
                    return False, f"Upload gagal di offset {offset}: {response.text}"
                
                offset += len(chunk)
                print(f"[i] Mengupload chunk {offset/1024/1024:.1f}MB", end='\r')
        
        # Step 3: Finalisasi upload dan publikasi
        finish_params = {
            'access_token': access_token,
            'upload_phase': 'finish',
            'video_id': video_id,
            'video_state': 'PUBLISHED',
            'description': description
        }
        finish_url = f"https://graph.facebook.com/{API_VERSION}/{parent_object}/video_reels"
        finish_response = requests.post(finish_url, data=finish_params)
        
        if finish_response.status_code == 200:
            return True, "Video berhasil dipublikasikan"
        else:
            return False, f"Finalisasi gagal: {finish_response.text}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

if __name__ == "__main__":
    os_type = check_os()
    print(f"[i] Sistem terdeteksi: {os_type.capitalize()}")

    if not check_ffmpeg():
        print("[!] FFmpeg tidak ditemukan!")
        print("    Panduan instalasi:")
        if os_type == 'windows':
            print("    Unduh FFmpeg dari https://ffmpeg.org/download.html")
        elif os_type in ['linux', 'termux']:
            print(f"    {'pkg' if os_type == 'termux' else 'sudo apt'} install ffmpeg")
        sys.exit(1)

    if len(sys.argv) != 2:
        print("Penggunaan: python main.py <path_video>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    config = get_config()
    
    status, message = upload_reels(video_path, "Judul Video", "Deskripsi #hashtag", config['access_token'], config['page_id'])
    print(f"[i] {message}")
