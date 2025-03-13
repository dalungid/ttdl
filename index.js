const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const { spawn } = require('child_process');
const fs = require('fs');

// Config
const ADMIN_NUMBER = '6285777785464@c.us'; // Nomor admin
const PYTHON_PATH = 'python3'; // Path ke Python (bisa 'python' di Windows)
const SCRIPT_PATH = 'main.py';

// Inisialisasi Client WhatsApp
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--single-process',
        '--disable-gpu',
        '--aggressive-cache-discard',
        '--disable-cache',
        '--disable-application-cache',
        '--disable-offline-load-stale-cache',
        '--disk-cache-size=0'
      ],
      executablePath: '/usr/bin/chromium-browser' // Pastikan path benar
    },
    qrTimeout: 0, // Nonaktifkan timeout QR
    authTimeout: 0 // Nonaktifkan timeout auth
  });

// Handle QR Code
client.on('qr', qr => {
    qrcode.generate(qr, { small: true });
    // Kirim QR ke admin via WA
    client.sendMessage(ADMIN_NUMBER, 'Scan QR Code ini:\n' + qr);
});

// Handle Ready
client.on('ready', () => {
    console.log('Client is ready!');
});
client.on('auth_failure', msg => {
    console.error('Auth failure:', msg);
  });
  
  client.on('disconnected', (reason) => {
    console.log('Client logged out:', reason);
  });
  
  client.on('loading_screen', (percent, message) => {
    console.log('Loading:', percent, message);
  });
// Handle Pesan
client.on('message', async msg => {
    try {
        const content = msg.body.toLowerCase();
        const from = msg.from;
        
        // Hanya proses command dengan prefix !
        if (!content.startsWith('!')) return;

        // Split command dan args
        const [command, ...args] = content.slice(1).split(' ');
        
        // Handle commands
        switch(command) {
            case 't':
            case 'tl':
            case 'y':
            case 'yl':
                handleMediaCommand(msg, command, args);
                break;
                
            case 'cektoken':
                handlePythonCommand(msg, 'cektoken');
                break;
                
            case 'updatetoken':
                handlePythonCommand(msg, 'updatetoken', args);
                break;
                
            case 'gantiwm':
                handlePythonCommand(msg, 'gantiwm', args);
                break;
                
            case 'gantifp':
                handlePythonCommand(msg, 'gantifp', args);
                break;
                
            default:
                msg.reply('Command tidak valid');
        }
    } catch (error) {
        console.error(error);
        msg.reply('Terjadi error saat memproses permintaan');
    }
});

// Fungsi handle command media
async function handleMediaCommand(msg, command, args) {
    const type = command[0]; // t/y
    const isList = command.length > 1 && command[1] === 'l';
    
    try {
        if (isList) {
            // Handle list dari file
            const media = await msg.downloadMedia();
            const filePath = `./temp_${Date.now()}.txt`;
            fs.writeFileSync(filePath, Buffer.from(media.data, 'base64'));
            
            runPythonScript(msg, [command, filePath]);
        } else {
            // Handle single URL
            const url = args[0];
            if (!url) return msg.reply('URL tidak valid');
            runPythonScript(msg, [command, url]);
        }
    } catch (error) {
        console.error(error);
        msg.reply('Gagal memproses file');
    }
}

// Fungsi handle command Python
function handlePythonCommand(msg, command, args = []) {
    runPythonScript(msg, [command, ...args]);
}

// Eksekusi script Python
function runPythonScript(msg, args) {
    const python = spawn(PYTHON_PATH, [SCRIPT_PATH, ...args]);
    let output = '';

    python.stdout.on('data', (data) => {
        output += data.toString();
    });

    python.stderr.on('data', (data) => {
        console.error(`Python Error: ${data}`);
        msg.reply('Terjadi error saat eksekusi script');
    });

    python.on('close', (code) => {
        if (code !== 0) return;
        // Format output dari Python
        const response = output.split('\n')
            .filter(line => line.startsWith('[WA]'))
            .map(line => line.replace('[WA] ', ''))
            .join('\n');
            
        msg.reply(response || 'Proses selesai');
    });
}

client.initialize();