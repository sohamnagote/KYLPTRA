const { app, BrowserWindow, dialog, ipcMain, Menu, session, shell } = require("electron");
const path = require("path");
const http = require("http");
const net = require("net");
const crypto = require("crypto");
const { spawn, execSync } = require("child_process");
const fs = require("fs");

let mainWindow = null;
let backendProcess = null;
let activePort = 8000;
const SESSION_TOKEN = crypto.randomBytes(32).toString("hex");

// Single-instance lock for clean desktop behavior
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

function findAvailablePort(preferred = 8000) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.on("error", () => {
      const ephem = net.createServer();
      ephem.unref();
      ephem.listen(0, "127.0.0.1", () => {
        const port = ephem.address().port;
        ephem.close(() => resolve(port));
      });
    });
    server.listen(preferred, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

function getDevPythonPath() {
  if (process.env.KLYPTRA_PYTHON && fs.existsSync(process.env.KLYPTRA_PYTHON)) {
    return process.env.KLYPTRA_PYTHON;
  }
  try {
    const found = execSync("where python", { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] })
      .split(/\r?\n/)
      .map(s => s.trim())
      .find(p => p && fs.existsSync(p) && !p.includes("WindowsApps"));
    if (found) return found;
  } catch (e) {}

  // Scan user's LocalAppData Python installations dynamically without hardcoding username
  const localAppData = process.env.LOCALAPPDATA || "";
  if (localAppData) {
    const pyRoot = path.join(localAppData, "Python");
    if (fs.existsSync(pyRoot)) {
      for (const entry of fs.readdirSync(pyRoot)) {
        const candidate = path.join(pyRoot, entry, "python.exe");
        if (fs.existsSync(candidate)) return candidate;
      }
    }
  }
  return "python";
}

function startBackend(port) {
  const isProd = app.isPackaged;
  const binDir = isProd
    ? path.join(process.resourcesPath, "bin")
    : path.join(__dirname, "..", "resources", "bin");

  const envVars = {
    ...process.env,
    PYTHONUNBUFFERED: "1",
    KLYPTRA_PORT: String(port),
    KLYPTRA_SESSION_TOKEN: SESSION_TOKEN,
    KLYPTRA_ENV: isProd ? "production" : "development",
    ...(fs.existsSync(binDir) ? { KLYPTRA_BIN_DIR: binDir } : {})
  };

  if (isProd) {
    const sidecarExe = path.join(process.resourcesPath, "backend", "klyptra-backend.exe");
    if (!fs.existsSync(sidecarExe)) {
      dialog.showErrorBox(
        "KLYPTRA Installation Error",
        "The local AI processing service could not be found. Please reinstall KLYPTRA."
      );
      app.quit();
      return;
    }
    backendProcess = spawn(sidecarExe, [], {
      cwd: path.dirname(sidecarExe),
      stdio: "ignore",
      windowsHide: true,
      env: envVars
    });
  } else {
    const pythonExe = getDevPythonPath();
    const projectRoot = path.join(__dirname, "..");
    backendProcess = spawn(
      pythonExe,
      ["-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", String(port), "--log-level", "warning"],
      {
        cwd: projectRoot,
        stdio: "pipe",
        windowsHide: true,
        env: envVars
      }
    );
    backendProcess.stderr.on("data", (data) => {
      console.error(`[Backend]: ${data.toString().trim()}`);
    });
  }

  backendProcess.on("exit", (code) => {
    if (code !== 0 && code !== null) {
      console.error(`[Desktop] Backend exited with code ${code}`);
    }
  });
}

function stopBackend() {
  if (backendProcess && backendProcess.pid) {
    try {
      if (process.platform === "win32") {
        execSync(`taskkill /pid ${backendProcess.pid} /T /F`, { stdio: "ignore", windowsHide: true });
      } else {
        backendProcess.kill("SIGTERM");
      }
    } catch (e) {}
    backendProcess = null;
  }
}

function waitForBackend(port, callback, retries = 45) {
  if (retries <= 0) {
    dialog.showErrorBox(
      "KLYPTRA Startup Error",
      "The local KLYPTRA engine failed to start in time. Please check your antivirus or free disk space and try again."
    );
    stopBackend();
    app.quit();
    return;
  }

  http.get(`http://127.0.0.1:${port}/api/health`, (res) => {
    if (res.statusCode === 200) {
      callback();
    } else {
      setTimeout(() => waitForBackend(port, callback, retries - 1), 400);
    }
  }).on("error", () => {
    setTimeout(() => waitForBackend(port, callback, retries - 1), 400);
  });
}

function createMainWindow(port) {
  if (app.isPackaged) {
    Menu.setApplicationMenu(null);
  }

  const iconPath = path.join(__dirname, "..", "build", "icon.ico");
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 880,
    minWidth: 1024,
    minHeight: 680,
    title: "KLYPTRA Studio",
    backgroundColor: "#fbf8ff",
    autoHideMenuBar: true,
    show: false,
    ...(fs.existsSync(iconPath) ? { icon: iconPath } : {}),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      devTools: !app.isPackaged
    }
  });

  // Attach per-session auth token exclusively to local KLYPTRA API calls
  session.defaultSession.webRequest.onBeforeSendHeaders(
    { urls: [`http://127.0.0.1:${port}/*`, `http://localhost:${port}/*`] },
    (details, callback) => {
      details.requestHeaders["X-Klyptra-Token"] = SESSION_TOKEN;
      callback({ requestHeaders: details.requestHeaders });
    }
  );

  // Restrict external navigation safely
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https://")) {
      shell.openExternal(url);
    }
    return { action: "deny" };
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.loadURL(`http://127.0.0.1:${port}/`);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// Native Windows file/folder pickers for cleaner UX
ipcMain.handle("klyptra:select-folder", async () => {
  if (!mainWindow) return null;
  const res = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory", "createDirectory"]
  });
  return res.canceled || !res.filePaths.length ? null : res.filePaths[0];
});

ipcMain.handle("klyptra:select-video-file", async () => {
  if (!mainWindow) return null;
  const res = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile"],
    filters: [{ name: "Video Files", extensions: ["mp4", "mov", "mkv", "webm", "avi", "m4v"] }]
  });
  return res.canceled || !res.filePaths.length ? null : res.filePaths[0];
});

app.whenReady().then(async () => {
  activePort = await findAvailablePort(8000);
  startBackend(activePort);
  waitForBackend(activePort, () => {
    createMainWindow(activePort);
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow(activePort);
    }
  });
});

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  stopBackend();
});
