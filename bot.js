const { Telegraf } = require('telegraf');
const fs = require('fs');
const axios = require('axios');
const { exec } = require('child_process');

// Token Bot Telegram
const BOT_TOKEN = '7752275862:AAGTbTNMmmk9s7eENaQL9Er56VMS6CzO5cE';

// Path ke config.json
const CONFIG_PATH = './config.json';

// Helper untuk membaca config.json
function readConfig() {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
}

// Helper untuk menulis ke config.json
function writeConfig(config) {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 4));
}

// Antrian video
let videoQueue = [];
let isProcessing = false;

// Fungsi hitung mundur
function countdown(ctx, totalSeconds, callback) {
    let remaining = totalSeconds;

    function sendCountdown() {
        if (remaining > 0) {
            const minutes = Math.floor(remaining / 60);
            const seconds = remaining % 60;
            ctx.reply(`Memulai pemrosesan video berikutnya dalam ${minutes} Menit ${seconds} Detik...`);
            remaining--;
            setTimeout(sendCountdown, 1000);
        } else {
            callback();
        }
    }

    sendCountdown();
}

// Fungsi untuk memproses antrian
function processQueue(ctx) {
    if (isProcessing || videoQueue.length === 0) return;

    isProcessing = true;
    const videoUrl = videoQueue.shift();

    ctx.reply(`Memproses video: ${videoUrl}`);

    // Panggil main.py untuk memproses video
    exec(`python3 main.py "${videoUrl}"`, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error: ${stderr}`);
            ctx.reply(`Gagal memproses video: ${stderr}`);
        } else {
            ctx.reply(`Video berhasil diproses!`);
        }

        isProcessing = false;

        // Jika masih ada video di antrian, lanjutkan dengan jeda 5 menit
        if (videoQueue.length > 0) {
            countdown(ctx, 300, () => {
                processQueue(ctx);
            });
        }
    });
}

// Inisialisasi bot
const bot = new Telegraf(BOT_TOKEN);

// Menu utama
bot.start((ctx) => {
    ctx.reply(
        "Selamat datang di Bot Tools Reels!\n\n" +
        "/cektoken - Cek status token Facebook\n" +
        "/gantifp - Ganti ID Page Facebook\n" +
        "/gantiwm - Ganti teks watermark\n" +
        "/help - Panduan penggunaan bot\n\n" +
        "Kirim link TikTok langsung untuk memproses video!"
    );
});

// Tangkap input URL TikTok
bot.on('text', (ctx) => {
    const input = ctx.message.text.trim();

    // Validasi apakah input adalah URL TikTok
    if (input.startsWith('http')) {
        videoQueue.push(input);
        ctx.reply(`Link TikTok ditambahkan ke antrian. Total antrian: ${videoQueue.length}`);

        // Jika tidak sedang memproses, mulai proses antrian
        if (!isProcessing) {
            processQueue(ctx);
        }
    } else {
        ctx.reply("Silakan kirim link TikTok yang valid.");
    }
});

// /cektoken
let pendingTokenUpdate = {};
bot.command('cektoken', (ctx) => {
    const config = readConfig();
    const token = config.access_token;

    if (!token) {
        ctx.reply("Token tidak ditemukan. Silakan masukkan token baru.");
        pendingTokenUpdate[ctx.chat.id] = true;
        return;
    }

    // Validasi token menggunakan Graph API Debugger
    const debugUrl = `https://graph.facebook.com/debug_token?input_token=${token}&access_token=${token}`;
    axios.get(debugUrl)
        .then((response) => {
            const data = response.data.data;
            if (data.is_valid) {
                const permissions = data.scopes || [];
                const requiredPermissions = ['pages_show_list', 'pages_read_engagement', 'pages_manage_posts'];
                const missingPermissions = requiredPermissions.filter(perm => !permissions.includes(perm));

                if (missingPermissions.length > 0) {
                    ctx.reply(
                        "Token valid, tetapi izin berikut belum dipenuhi:\n" +
                        missingPermissions.join(", ") +
                        "\nSilakan perbarui token."
                    );
                    pendingTokenUpdate[ctx.chat.id] = true;
                } else {
                    ctx.reply("Token valid dan memenuhi semua persyaratan!");
                }
            } else {
                ctx.reply("Token tidak valid. Silakan masukkan token baru.");
                pendingTokenUpdate[ctx.chat.id] = true;
            }
        })
        .catch(() => {
            ctx.reply("Gagal memeriksa token. Pastikan token benar.");
            pendingTokenUpdate[ctx.chat.id] = true;
        });
});

// Tangkap input token baru
bot.on('text', (ctx) => {
    if (pendingTokenUpdate[ctx.chat.id]) {
        const newToken = ctx.message.text.trim();
        const config = readConfig();
        config.access_token = newToken;
        writeConfig(config);
        ctx.reply("Token berhasil diperbarui!");
        delete pendingTokenUpdate[ctx.chat.id];
    }
});

// /gantifp
let pendingPageIdUpdate = {};
bot.command('gantifp', (ctx) => {
    ctx.reply("Silakan masukkan ID Page Facebook baru.\nKetik /batal untuk kembali ke menu utama.");
    pendingPageIdUpdate[ctx.chat.id] = true;
});

// Tangkap input ID Page baru
bot.on('text', (ctx) => {
    if (pendingPageIdUpdate[ctx.chat.id]) {
        const newPageId = ctx.message.text.trim();
        if (newPageId === '/batal') {
            ctx.reply("Proses dibatalkan.");
            delete pendingPageIdUpdate[ctx.chat.id];
            return;
        }

        const config = readConfig();
        config.page_id = newPageId;
        writeConfig(config);
        ctx.reply(`ID Page berhasil diperbarui menjadi: ${newPageId}`);
        delete pendingPageIdUpdate[ctx.chat.id];
    }
});

// /gantiwm
let pendingTextUpdate = {};
bot.command('gantiwm', (ctx) => {
    ctx.reply("Silakan masukkan teks watermark baru.\nKetik /batal untuk kembali ke menu utama.");
    pendingTextUpdate[ctx.chat.id] = true;
});

// Tangkap input teks watermark baru
bot.on('text', (ctx) => {
    if (pendingTextUpdate[ctx.chat.id]) {
        const newText = ctx.message.text.trim();
        if (newText === '/batal') {
            ctx.reply("Proses dibatalkan.");
            delete pendingTextUpdate[ctx.chat.id];
            return;
        }

        const config = readConfig();
        config.text = newText;
        writeConfig(config);
        ctx.reply(`Teks watermark berhasil diperbarui menjadi: ${newText}`);
        delete pendingTextUpdate[ctx.chat.id];
    }
});

// /help
bot.command('help', (ctx) => {
    ctx.reply(
        "Panduan Penggunaan Bot:\n\n" +
        "/cektoken - Periksa status token Facebook\n" +
        "/gantifp - Ganti ID Page Facebook\n" +
        "/gantiwm - Ganti teks watermark\n" +
        "/help - Tampilkan panduan ini\n\n" +
        "Fitur Utama:\n" +
        "- Kirim link TikTok langsung untuk memproses video.\n" +
        "- Bot akan memproses video secara otomatis dengan jeda 5 menit antar video.\n" +
        "- Antrian video diproses satu per satu."
    );
});

// Jalankan bot
bot.launch();
console.log("[✓] Bot Telegram aktif!");

// Handle shutdown
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));