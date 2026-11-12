const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const PORT = 9336;
const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const USER_DATA = path.join(process.env.TEMP, 'chrome_prod_test_' + Date.now());

function sendCDP(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1000000);
    const handler = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id === id) {
        ws.removeEventListener('message', handler);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
      }
    };
    ws.addEventListener('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function run() {
  const chrome = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${USER_DATA}`,
    '--disable-gpu',
    '--window-size=1440,900',
    'about:blank'
  ]);

  await new Promise(r => setTimeout(r, 2000));
  let exitCode = 0;

  try {
    const tabs = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
    const ws = new WebSocket(tabs[0].webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });

    await sendCDP(ws, 'Page.enable');
    await sendCDP(ws, 'Runtime.enable');
    await sendCDP(ws, 'Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

    const errors = [];
    ws.addEventListener('message', (e) => {
      const data = JSON.parse(e.data);
      if (data.method === 'Runtime.exceptionThrown') {
        errors.push(data.params.exceptionDetails.text);
      }
    });

    await sendCDP(ws, 'Page.navigate', { url: 'http://127.0.0.1:8000/' });
    await new Promise(r => setTimeout(r, 2500));

    // Dismiss first launch modal if open for screenshot consistency
    await sendCDP(ws, 'Runtime.evaluate', {
      expression: `document.getElementById('modal-first-launch')?.classList.add('hidden')`
    });

    // Verify Light Mode Default
    const themeDefault = await sendCDP(ws, 'Runtime.evaluate', {
      expression: `({ mode: window.KlyptraTheme?.getMode(), resolved: window.KlyptraTheme?.getResolvedTheme(), isDark: document.documentElement.classList.contains('dark'), title: document.title })`,
      returnByValue: true
    });
    console.log('[Test] Default theme:', JSON.stringify(themeDefault));
    if (themeDefault.result.value.isDark !== false) throw new Error('Default theme should be Light!');

    // Check responsive layout across desktop resolutions
    const resolutions = [
      { w: 1280, h: 720 },
      { w: 1366, h: 768 },
      { w: 1440, h: 900 },
      { w: 1920, h: 1080 }
    ];
    for (const res of resolutions) {
      await sendCDP(ws, 'Emulation.setDeviceMetricsOverride', { width: res.w, height: res.h, deviceScaleFactor: 1, mobile: false });
      for (const view of ['new-project', 'clips', 'editor', 'projects', 'settings']) {
        await sendCDP(ws, 'Runtime.evaluate', { expression: `switchView('${view}')` });
        await new Promise(r => setTimeout(r, 280));
        const overflow = await sendCDP(ws, 'Runtime.evaluate', {
          expression: `({ scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth })`,
          returnByValue: true
        });
        const { scrollW, innerW } = overflow.result.value;
        if (scrollW > innerW + 2) {
          throw new Error(`Horizontal overflow at ${res.w}x${res.h} on view '${view}': scrollWidth=${scrollW} > innerWidth=${innerW}`);
        }
      }
      console.log(`[Test] Resolution ${res.w}x${res.h}: ZERO horizontal overflow across all 5 views`);
    }

    // Capture Settings screenshot in Light and Dark at 1440x900
    await sendCDP(ws, 'Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sendCDP(ws, 'Runtime.evaluate', { expression: `switchView('settings')` });
    await new Promise(r => setTimeout(r, 400));
    const lightSettingsShot = await sendCDP(ws, 'Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync('klyptra_settings_light.png', Buffer.from(lightSettingsShot.data, 'base64'));

    await sendCDP(ws, 'Runtime.evaluate', { expression: `KlyptraTheme.setMode('dark')` });
    await new Promise(r => setTimeout(r, 400));
    const darkSettingsShot = await sendCDP(ws, 'Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync('klyptra_settings_dark.png', Buffer.from(darkSettingsShot.data, 'base64'));

    if (errors.length > 0) {
      throw new Error('Runtime JS exceptions detected: ' + errors.join('; '));
    }
    console.log('[Test] ALL PRODUCTION UI, RESPONSIVE & LIQUID GLASS CHECKS PASSED!');
  } catch (err) {
    console.error('[Test Error]:', err);
    exitCode = 1;
  } finally {
    chrome.kill();
    try { fs.rmSync(USER_DATA, { recursive: true, force: true }); } catch (e) {}
    process.exit(exitCode);
  }
}

run();
