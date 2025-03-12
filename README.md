### **Dokumentasi**

#### **Fitur Utama**
1. **Pemrosesan Video Otomatis:**
   - Pengguna dapat mengirim URL TikTok langsung ke bot.
   - Bot akan menambahkan URL ke antrian dan memprosesnya satu per satu.
   - Jeda 5 menit antar video untuk menghindari spam atau overload.

2. **Antrian Video:**
   - Bot mendukung pemrosesan banyak video dalam antrian.
   - Status antrian ditampilkan kepada pengguna.

3. **Perintah Bot:**
   - `/cektoken`: Memeriksa status token Facebook.
   - `/gantifp`: Mengganti ID Page Facebook.
   - `/gantiwm`: Mengganti teks watermark.
   - `/help`: Menampilkan panduan penggunaan bot.

4. **Feedback Real-Time:**
   - Bot memberikan feedback tentang status pemrosesan video (sukses/gagal).
   - Hitung mundur ditampilkan sebelum memproses video berikutnya.

---

### **Cara Instalasi dan Penggunaan**

1. **Instal Dependensi**
   ```bash
   npm install
   ```

2. **Konfigurasi**
   - Isi file `config.json` dengan token Facebook, ID Page, dan teks watermark.

3. **Jalankan Bot**
   ```bash
   npm start
   ```

4. **Interaksi dengan Bot**
   - Kirim URL TikTok langsung ke bot.
   - Gunakan perintah `/cektoken`, `/gantifp`, `/gantiwm`, atau `/help` sesuai kebutuhan.

---

### **Catatan Penting**

1. **FFmpeg:**
   - Pastikan FFmpeg sudah terinstal di sistem Anda (`ffmpeg` harus tersedia di PATH).

2. **Token Facebook:**
   - Token Facebook harus memiliki izin:
     - `pages_show_list`
     - `pages_read_engagement`
     - `pages_manage_posts`

3. **Durasi Jeda:**
   - Jeda 5 menit dapat disesuaikan dengan mengubah nilai `300` di fungsi `countdown`.

4. **Error Handling:**
   - Bot memberikan pesan kesalahan jika terjadi error saat memproses video.

---