import requests
import sys
import os
import random
import json
import subprocess
import shutil
import platform
import time

# Konfigurasi Facebook API
API_VERSION = 'v22.0'

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

def check_token_validity(access_token):
    """
    Memeriksa apakah token valid dan memiliki izin yang diperlukan.
    """
    required_permissions = {
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts"
    }

    try:
        print("[i] Memeriksa validitas token...")
        # Endpoint untuk mendapatkan izin token
        permissions_url = f"https://graph.facebook.com/{API_VERSION}/me/permissions"
        params = {
            "access_token": access_token
        }
        response = requests.get(permissions_url, params=params)

        if response.status_code != 200:
            return False, f"Token tidak valid: {response.text}"

        permissions_data = response.json().get("data", [])
        granted_permissions = {
            perm["permission"] for perm in permissions_data if perm.get("status") == "granted"
        }

        # Periksa apakah semua izin yang diperlukan ada
        missing_permissions = required_permissions - granted_permissions
        if missing_permissions:
            return False, f"Token kekurangan izin: {', '.join(missing_permissions)}"

        return True, "Token valid dan memiliki semua izin yang diperlukan."

    except Exception as e:
        return False, f"Error saat memeriksa token: {str(e)}"


def update_config_with_new_token(new_token):
    """
    Memperbarui file config.json dengan token baru.
    """
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)

        config["access_token"] = new_token

        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)

        print("[✓] Token berhasil diperbarui di config.json")
    except Exception as e:
        print(f"[!] Gagal memperbarui token di config.json: {str(e)}")


def prompt_for_new_token():
    """
    Meminta pengguna untuk memasukkan token baru.
    """
    while True:
        new_token = input("[?] Masukkan token baru: ").strip()
        if not new_token:
            print("[!] Token tidak boleh kosong!")
            continue

        # Periksa validitas token baru
        is_valid, message = check_token_validity(new_token)
        if is_valid:
            print("[✓] Token baru valid.")
            update_config_with_new_token(new_token)
            return new_token
        else:
            print(f"[!] Token tidak valid: {message}")


def upload_to_facebook(video_path, title, description, access_token, page_id):
    try:
        # Step 1: Periksa validitas token sebelum melanjutkan
        is_valid, message = check_token_validity(access_token)
        if not is_valid:
            print(f"[!] Token tidak valid: {message}")
            new_token = prompt_for_new_token()
            access_token = new_token  # Gunakan token baru untuk proses selanjutnya

        # Step 2: Inisiasi upload session
        print("[i] Memulai inisiasi session upload...")
        start_url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/video_reels"
        start_data = {
            "upload_phase": "START",
            "access_token": access_token
        }
        start_response = requests.post(start_url, json=start_data)
        
        if start_response.status_code != 200:
            return False, f"Inisiasi gagal: {start_response.text}"
        
        start_json = start_response.json()
        video_id = start_json.get('video_id')
        upload_url = start_json.get('upload_url')
        
        if not video_id or not upload_url:
            return False, "Invalid response dari Facebook: video_id/upload_url tidak ditemukan"

        # Step 3: Upload video utuh
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
        
        # Step 4: Cek status upload
        print("[i] Memeriksa status upload...")
        status_url = f"https://graph.facebook.com/{API_VERSION}/{video_id}"
        status_params = {
            "access_token": access_token,
            "fields": "status"
        }
        
        max_retries = 10
        for _ in range(max_retries):
            status_response = requests.get(status_url, params=status_params)
            status_data = status_response.json().get('status', {})
            
            if status_data.get('uploading_phase', {}).get('status') == 'complete':
                break
            time.sleep(5)
        else:
            return False, "Timeout menunggu upload selesai"

        # Step 5: Publish Reels
        print("[i] Mempublikasikan Reels...")
        publish_url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/video_reels"
        publish_data = {
            "access_token": access_token,
            "video_id": video_id,
            "upload_phase": "finish",
            "video_state": "PUBLISHED",
            "title": title,
            "description": description
        }
        publish_response = requests.post(publish_url, data=publish_data)
        
        if publish_response.status_code == 200:
            return True, "Video berhasil dipublikasikan"
        else:
            return False, f"Publish gagal: {publish_response.text}"

    except Exception as e:
        return False, f"Error: {str(e)}"


def download_tiktok_video(url):
    try:
        output_dir = 'result'
        os.makedirs(output_dir, exist_ok=True)
        config = get_config()
        
        # Unduh video dari TikWM API
        print("[i] Mengambil data video dari TikTok...")
        api_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(api_url)
        data = response.json()

        if data.get('code') != 0:
            print(f"Error API: {data.get('msg', 'Tidak dapat mengambil data video')}")
            return

        video_data = data.get('data', {})
        video_url = video_data.get('play') or video_data.get('wmplay')
        title = config['text']
        description = video_data.get('title')

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
        print("[i] Memproses video dengan FFmpeg...")
        result = subprocess.run(ffmpeg_cmd, capture_output=True)
        if result.returncode != 0:
            print("Error FFmpeg:")
            print(result.stderr.decode())
            return

        # Upload ke Facebook
        print("\n[i] Memulai proses upload ke Facebook Reels...")
        success, message = upload_to_facebook(
            video_path=output_path,
            title=title,
            description=description,
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