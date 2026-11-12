const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const ROOT_DIR = __dirname;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.ttf': 'font/ttf',
  '.md': 'text/markdown; charset=utf-8'
};

const navScript = `
<script>
(function() {
  const routes = {
    'dashboard': '/dashboard_first_launch/code.html',
    'video-editor': '/video_editor_empty_state/code.html',
    'ai-processing': '/ai_processing_idle_state/code.html',
    'generated-clips': '/generated_clips_empty_state/code.html',
    'my-projects': '/my_projects_empty_state/code.html',
    'export-history': '/export_history_empty_state/code.html',
    'settings': '/settings_first_launch/code.html',
    'new-project': '/new_project_empty_state/code.html'
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-path]').forEach(el => {
      const p = el.getAttribute('data-path');
      if (routes[p]) {
        el.setAttribute('href', routes[p]);
      }
    });
  });

  document.addEventListener('click', (e) => {
    const link = e.target.closest('[data-path]');
    if (link) {
      const p = link.getAttribute('data-path');
      if (routes[p]) {
        e.preventDefault();
        window.location.href = routes[p];
      }
    }
  });
})();
</script>
`;

const server = http.createServer((req, res) => {
  let reqPath = decodeURI(req.url.split('?')[0]);

  if (reqPath === '/' || reqPath === '') {
    res.writeHead(302, { Location: '/dashboard_first_launch/code.html' });
    res.end();
    return;
  }

  let filePath = path.join(ROOT_DIR, reqPath);

  // Security check to prevent directory traversal
  if (!filePath.startsWith(ROOT_DIR)) {
    res.writeHead(403);
    res.end('Access Denied');
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('404 Not Found');
      return;
    }

    if (stats.isDirectory()) {
      filePath = path.join(filePath, 'code.html');
      if (!fs.existsSync(filePath)) {
        filePath = path.join(path.dirname(filePath), 'index.html');
      }
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (readErr, content) => {
      if (readErr) {
        res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('500 Internal Server Error');
        return;
      }

      if (ext === '.html') {
        let htmlStr = content.toString('utf-8');
        if (htmlStr.includes('</body>')) {
          htmlStr = htmlStr.replace('</body>', `${navScript}</body>`);
        } else {
          htmlStr += navScript;
        }
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(htmlStr);
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content);
      }
    });
  });
});

server.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}/`);
  console.log(`Dashboard available at http://localhost:${PORT}/dashboard_first_launch/code.html`);
});

