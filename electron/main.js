const { app, BrowserWindow, ipcMain, Tray, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let tray;
let pythonProcess;

async function callPythonAPI(endpoint, data = null) {
  const url = `http://localhost:3030/${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(url, {
      method: data ? 'POST' : 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: data ? JSON.stringify(data) : undefined,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Erro conectando ao Python:', error);
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, 'icons', 'merlin.png'),
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'electron-app', 'index.html'));

  // Exibe somente quando tudo estiver pronto para evitar tela branca.
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Bandeja com ações básicas do app.
  tray = new Tray(path.join(__dirname, 'icons', 'merlin-tray.png'));
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Abrir Merlin',
      click: () => mainWindow.show(),
    },
    {
      label: 'Sair',
      click: () => {
        if (pythonProcess) pythonProcess.kill();
        app.quit();
      },
    },
  ]);

  tray.setToolTip('Merlin IA');
  tray.setContextMenu(contextMenu);
  tray.on('click', () => mainWindow.show());
}

function startPythonBackend() {
  // Backend Python iniciado em processo filho (API HTTP local).
  const projectRoot = path.join(__dirname, '..');
  const pythonExec = path.join(projectRoot, '.venv', 'bin', 'python3');
  const apiScript = path.join(projectRoot, 'merlin_api.py');

  pythonProcess = spawn(pythonExec, [apiScript, '--port', '3030']);

  pythonProcess.stdout.on('data', (data) => {
    const text = data.toString();
    console.log(`🐍 API: ${text}`);
    if (text.includes('Running on') && mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('backend-ready');
    }
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`🐍 API ERRO: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`🐍 API encerrada com código ${code}`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('backend-stopped');
    }
  });
}

app.whenReady().then(() => {
  startPythonBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  // No macOS, é comum manter o app ativo mesmo sem janelas abertas.
  if (process.platform !== 'darwin') {
    if (pythonProcess) pythonProcess.kill();
    app.quit();
  }
});

app.on('before-quit', () => {
  if (pythonProcess) pythonProcess.kill();
});

// IPC controlado: frontend não acessa Node diretamente, apenas estes canais.
ipcMain.handle('ask-merlin', async (_event, question) => {
  try {
    const result = await callPythonAPI('ask', { question });
    return { answer: result.answer };
  } catch (error) {
    return {
      answer: `⚠️ Erro de conexão com o backend. Verifique se o Python está rodando.\n\nDetalhes: ${error.message}`,
    };
  }
});

ipcMain.handle('get-documents', async () => {
  try {
    const result = await callPythonAPI('documents');
    return { documents: result.documents };
  } catch (error) {
    return { documents: [], error: error.message };
  }
});
