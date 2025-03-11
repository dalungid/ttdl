import requests
import sys
import os
import random
import json
import subprocess

def generate_random_number():
    return random.randint(100000, 999999)

def get_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except:
        return {"text": "FB: GameBoo", "font_size": 24, "font_color": "#FFFFFF@0.7"}

def download_tiktok_video(url):
    try:
        # Membuat folder result jika belum ada
        output_dir = 'result'
        os.makedirs(output_dir, exist_ok=True)

        # Mengambil konfigurasi
        config = get_config()
        text = config.get("text", "FB: GameBoo")
        font_size = config.get("font_size", 24)
        font_color = config.get("font_color", "#FFFFFF@0.7")

        # Mengirim permintaan ke API
        api_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(api_url)
        data = response.json()

        if data.get('code') != 0:
            print(f"Error: {data.get('msg', 'Unknown error')}")
            return

        # Mendapatkan URL video
        video_data = data.get('data', {})
        video_url = video_data.get('play') or video_data.get('wmplay')
        
        if not video_url:
            print("Tidak dapat menemukan URL video")
            return

        # Mengunduh video
        video_response = requests.get(video_url)
        video_response.raise_for_status()

        # Menyimpan video sementara
        temp_filename = f"temp_video_{generate_random_number()}.mp4"
        with open(temp_filename, 'wb') as f:
            f.write(video_response.content)

        # Membuat nama file output
        output_filename = f"filmora-project-{generate_random_number()}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        # Konfigurasi FFmpeg
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', temp_filename,
            '-vf', f"drawtext=text='{text}':fontcolor={font_color}:fontsize={font_size}:x=10:y=(h-text_h)/2:box=1:boxcolor=#000000@0.5:boxborderw=5",
            '-c:a', 'copy',
            output_path
        ]

        # Menjalankan FFmpeg
        subprocess.run(ffmpeg_cmd, check=True)
        os.remove(temp_filename)  # Hapus file sementara

        print(f"\nVideo berhasil diproses dan disimpan di: {output_path}")

    except requests.exceptions.RequestException as e:
        print(f"Error jaringan: {str(e)}")
    except subprocess.CalledProcessError as e:
        print(f"Error FFmpeg: {str(e)}")
    except Exception as e:
        print(f"Error tak terduga: {str(e)}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Penggunaan: python tiktok_downloader.py <URL_TikTok>")
        sys.exit(1)
    
    # Cek ketersediaan FFmpeg
    if not subprocess.run(['which', 'ffmpeg'], capture_output=True).stdout:
        print("ERROR: FFmpeg tidak terinstal!")
        print("Silakan instal FFmpeg terlebih dahulu")
        sys.exit(1)

    tiktok_url = sys.argv[1]
    download_tiktok_video(tiktok_url)