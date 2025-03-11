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
        # Step 1: Inisiasi upload session
        parent_object = page_id if page_id else 'me'
        start_url = f"https://graph.facebook.com/{API_VERSION}/{parent_object}/video_reels"
        file_size = os.path.getsize(video_path)

        start_params = {
            'upload_phase': 'start',
            'access_token': access_token,
            'file_size': file_size
        }
        start_response = requests.post(start_url, data=start_params)
        start_data = start_response.json()

        if 'video_id' not in start_data:
            return False, f"Gagal inisiasi: {start_data.get('error', {}).get('message', 'Unknown error')}"

        video_id = start_data['video_id']
        upload_url = start_data['upload_url']
        print(f"[i] Video ID: {video_id}")

        # Step 2: Upload video (tanpa chunking)
        headers = {
            'Authorization': f'OAuth {access_token}',
            'offset': '0',
            'file_size': str(file_size),
            'Content-Type': 'application/octet-stream'
        }

        with open(video_path, 'rb') as f:
            response = requests.post(
                upload_url,
                headers=headers,
                data=f
            )

        if response.status_code != 200 or not response.json().get('success'):
            return False, f"Upload gagal: {response.text}"

        print("[✓] Video berhasil diupload")

        # Step 3: Finalisasi dan publish
        finish_params = {
            'access_token': access_token,
            'upload_phase': 'finish',
            'video_state': 'PUBLISHED',
            'title': title,
            'description': description
        }
        finish_url = f"https://graph.facebook.com/{API_VERSION}/{parent_object}/video_reels"
        finish_response = requests.post(finish_url, data=finish_params)

        if finish_response.status_code == 200 and finish_response.json().get('success'):
            return True, "Video berhasil dipublikasikan"
        else:
            return False, f"Finalisasi gagal: {finish_response.text}"

    except Exception as e:
        return False, f"Error: {str(e)}"

def download_tiktok_video(url):
    try:
        output_dir = 'result'
        os.makedirs(output_dir, exist_ok=True)
        config = get_config()

        # Unduh video dari TikWM API
        api_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(api_url)
        data = response.json()

        if data.get('code') != 0:
            print(f"Error API: {data.get('msg', 'Tidak dapat mengambil data video')}")
            return

        video_data = data.get('data', {})
        video_url = video_data.get('play') or video_data.get('wmplay')
        title = video_data.get('title', 'No Title')

        if not video_url:
            print("Error: URL video tidak ditemukan")
            return

        # Unduh video sementara
        temp_input = f"temp_{generate_random_number()}.mp4"
        with open(temp_input, 'wb') as f:
            f.write(requests.get(video_url).content)

        # Konfigurasi FFmpeg
        output_filename = f"filmora-project-{generate_random_number()}.mp4"
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

        # Jalankan FFmpeg
        result = subprocess.run(ffmpeg_cmd, capture_output=True)
        if result.returncode != 0:
            print("Error FFmpeg:")
            print(result.stderr.decode())
            return

        # Upload ke Facebook Reels
        print("\n[i] Memulai proses upload ke Facebook Reels...")
        success, message = upload_reels(
            video_path=output_path,
            title=title,
            description=config['text'],
            access_token=config['access_token'],
            page_id=config['page_id']
        )

        if success:
            print(f"\n[✓] {message}")
            os.remove(output_path)
            print(f"[✓] File {output_filename} berhasil dihapus")
        else:
            print(f"\n[!] {message}")
            print("[i] File tetap disimpan di folder result untuk diupload manual")

    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if os.path.exists(temp_input):
            os.remove(temp_input)

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
        print("Penggunaan: python main.py <URL_TikTok>")
        sys.exit(1)

    download_tiktok_video(sys.argv[1])