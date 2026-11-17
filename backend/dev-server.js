// Local stand-in for Vercel, for trying the app and admin page without deploying.
// Keeps everything in memory, so it is empty again after a restart.
//
//   cd backend && node dev-server.js        # http://localhost:8787, keys "dev-upload" / "dev-admin"

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { memoryStore } from './lib/store.js';
import { makeHandler as participants } from './api/participants.js';
import { makeHandler as sessions } from './api/sessions.js';
import { makeHandler as results } from './api/results.js';

process.env.UPLOAD_KEY ??= 'dev-upload';
process.env.ADMIN_KEY ??= 'dev-admin';
const PORT = Number(process.env.PORT || 8787);
const store = memoryStore();
const routes = {
  '/api/participants': participants(async () => store),
  '/api/sessions': sessions(async () => store),
  '/api/results': results(async () => store),
};

createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  if (url.pathname === '/' || url.pathname === '/admin.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(await readFile(new URL('./admin.html', import.meta.url)));
  }
  const route = routes[url.pathname];
  if (!route) {
    res.writeHead(404);
    return res.end('Not found');
  }
  let raw = '';
  for await (const chunk of req) raw += chunk;
  req.body = raw;
  req.query = Object.fromEntries(url.searchParams);
  // The few response helpers Vercel adds.
  res.status = code => { res.statusCode = code; return res; };
  res.json = value => { res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(value)); };
  await route(req, res);
}).listen(PORT, () => console.log(`Study backend on http://localhost:${PORT} (upload key "${process.env.UPLOAD_KEY}", admin key "${process.env.ADMIN_KEY}")`));
