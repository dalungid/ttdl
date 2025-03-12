import requests
import sys
import os
import random
import json
import subprocess
import shutil
import platform
import time
from pytube import YouTube

# Konfigurasi
API_VERSION = 'v22.0'
CONFIG_FILE = 'config.json'

def print_wa(message):
    print(f"[WA] {message}")

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

def generate_random_number():
    return f"{random.randint(100000, 999999)}"

def get_config():
    default = {
        "text": "FB: GameBoo",
        "font_size": 24,
        "font_color": "#FFFFFF",
        "alpha": 0.7,
        "shadow_offset": 1,
        "access_token": "YOUR_TOKEN_HERE",
        "page_id": ""
    }
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return {**default, **config}
    except:
        return default

def update_config(new_data):
    config = get_config()
    config.update(new_data)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def check_token_validity(token):
    try:
        url = f"https://graph.facebook.com/{API_VERSION}/me?access_token={token}"
        response = requests.get(url)
        return response.status_code == 200
    except:
        return False

def upload_to_facebook(video_path, title, description):
    config = get_config()
    access_token = config['access_token']
    page_id = config['page_id']

    if not check_token_validity(access_token):
        print_wa("❌ Token Facebook expired! Harap perbarui token dengan !updatetoken")
        return False, "Token tidak valid"

    try:
        # Step 1: Inisiasi upload session
        print("[i] Memulai inisiasi session upload...")
        start_url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/video_reels"
        start_data = {
            "upload_phase": "start",
            "access_token": access_token
        }
        start_response = requests.post(start_url, data=start_data)
        
        if start_response.status_code != 200:
            return False, f"Inisiasi gagal: {start_response.text}"
        
        start_json = start_response.json()
        video_id = start_json.get('video_id')
        upload_url = start_json.get('upload_url')
        
        if not video_id or not upload_url:
            return False, "Invalid response dari Facebook"

        # Step 2: Upload video
        print(f"[i] Mengupload video ke Facebook (ID: {video_id})...")
        file_size = os.path.getsize(video_path)
        headers = {
            "Authorization": f"OAuth {access_token}",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Type": "application/octet-stream"
        }
        
        with open(video_path, 'rb') as f:
            upload_response = requests.post(upload_url, headers=headers, data=f)
        
        if upload_response.status_code != 200:
            return False, f"Upload gagal: {upload_response.text}"

        # Step 3: Cek status upload
        print("[i] Memeriksa status upload...")
        status_url = f"https://graph.facebook.com/{API_VERSION}/{video_id}"
        status_params = {"fields": "status", "access_token": access_token}
        
        for _ in range(10):
            time.sleep(5)
            status_response = requests.get(status_url, params=status_params)
            if status_response.json().get('status', {}).get('video_status', '') == 'ready':
                break
        else:
            return False, "Timeout menunggu upload selesai"

        # Step 4: Publish
        print("[i] Mempublikasikan Reels...")
        publish_url = f"https://graph.facebook.com/{API_VERSION}/{video_id}"
        publish_data = {
            "access_token": access_token,
            "description": description,
            "published": "true"
        }
        publish_response = requests.post(publish_url, data=publish_data)
        
        if publish_response.status_code == 200:
            return True, "Video berhasil dipublikasikan"
        else:
            return False, f"Publish gagal: {publish_response.text}"

    except Exception as e:
        return False, f"Error: {str(e)}"

def process_video(temp_input, description):
    try:
        config = get_config()
        output_dir = 'result'
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = f"processed_{generate_random_number()}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        filter_complex = (
            f"drawtext=text='{config['text']}':"
            f"fontcolor='{config['font_color']}@{config['alpha']}':"
            f"fontsize={config['font_size']}:"
            f"x=10:y=(h-text_h)/2:"
            f"shadowx={config['shadow_offset']}:"
            f"shadowy={config['shadow_offset']}:"
            f"shadowcolor={config['font_color']}@{config['alpha']}"
        )

        ffmpeg_cmd = [
            'ffmpeg',
            '-y',
            '-i', temp_input,
            '-vf', filter_complex,
            '-c:v', 'libx264',
            '-b:v', '8M',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_path
        ]

        result = subprocess.run(ffmpeg_cmd, capture_output=True)
        if result.returncode != 0:
            print_wa("❌ Gagal memproses video")
            print(result.stderr.decode())
            return None
        
        return output_path

    except Exception as e:
        print_wa(f"❌ Error processing: {str(e)}")
        return None

def handle_tiktok(url):
    try:
        print_wa("⏳ Memulai proses TikTok...")
        
        # Download video
        api_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(api_url)
        data = response.json()

        if data.get('code') != 0:
            print_wa("❌ Gagal mengambil video TikTok")
            return False

        video_url = data['data'].get('play') or data['data'].get('wmplay')
        temp_input = f"temp_{generate_random_number()}.mp4"
        
        with open(temp_input, 'wb') as f:
            f.write(requests.get(video_url).content)

        # Process video
        output_path = process_video(temp_input, data['data']['title'])
        if not output_path:
            return False

        # Upload
        success, message = upload_to_facebook(
            output_path,
            get_config()['text'],
            data['data']['title']
        )
        
        if success:
            print_wa("✅ Berhasil upload ke Facebook!")
            os.remove(output_path)
        else:
            print_wa(f"❌ Gagal upload: {message}")
        
        os.remove(temp_input)
        return True

    except Exception as e:
        print_wa(f"❌ Error: {str(e)}")
        return False

def handle_youtube(url):
    try:
        print_wa("⏳ Memulai proses YouTube...")
        
        yt = YouTube(url)
        video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        temp_input = f"temp_{generate_random_number()}.mp4"
        video.download(filename=temp_input)

        # Process video
        output_path = process_video(temp_input, yt.title)
        if not output_path:
            return False

        # Upload
        success, message = upload_to_facebook(
            output_path,
            get_config()['text'],
            yt.title
        )
        
        if success:
            print_wa("✅ Berhasil upload ke Facebook!")
            os.remove(output_path)
        else:
            print_wa(f"❌ Gagal upload: {message}")
        
        os.remove(temp_input)
        return True

    except Exception as e:
        print_wa(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan: python main.py <command> [args...]")
        sys.exit(1)

    # Check FFmpeg
    if not check_ffmpeg():
        print_wa("❌ FFmpeg tidak terinstall!")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    try:
        if command == 't':
            for url in args:
                handle_tiktok(url)
        elif command == 'tl':
            with open(args[0], 'r') as f:
                for url in f.read().splitlines():
                    handle_tiktok(url)
        elif command == 'y':
            for url in args:
                handle_youtube(url)
        elif command == 'yl':
            with open(args[0], 'r') as f:
                for url in f.read().splitlines():
                    handle_youtube(url)
        elif command == 'cektoken':
            valid = check_token_validity(get_config()['access_token'])
            status = "VALID ✅" if valid else "EXPIRED ❌"
            print_wa(f"Status Token: {status}")
        elif command == 'updatetoken':
            update_config({'access_token': args[0]})
            print_wa("✅ Token berhasil diperbarui")
        elif command == 'gantiwm':
            update_config({'text': ' '.join(args)})
            print_wa("✅ Watermark berhasil diubah")
        elif command == 'gantifp':
            update_config({'page_id': args[0]})
            print_wa("✅ Page ID berhasil diubah")
        else:
            print_wa("❌ Command tidak dikenali")

    except Exception as e:
        print_wa(f"❌ Error sistem: {str(e)}")