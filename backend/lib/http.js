// Shared request helpers for the API routes.

import { createHash, timingSafeEqual } from 'node:crypto';
import { blobStore } from './store.js';

let storePromise;
export function defaultStore() {
  storePromise ??= blobStore();
  return storePromise;
}

// UPLOAD_KEY is shared with the study laptops; ADMIN_KEY only with the team for the results page.
export function keyOk(req, envName) {
  const want = process.env[envName];
  if (!want) return null;
  const got = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
  const a = createHash('sha256').update(got).digest();
  const b = createHash('sha256').update(want).digest();
  return timingSafeEqual(a, b);
}

export function requireKey(req, res, envName) {
  const ok = keyOk(req, envName);
  if (ok === null) {
    res.status(500).json({ error: `${envName} isn't set. Add it as an environment variable in Vercel, then redeploy.` });
    return false;
  }
  if (!ok) {
    res.status(401).json({ error: 'That key isn’t right.' });
    return false;
  }
  return true;
}

export function body(req) {
  const raw = req.body;
  if (typeof raw === 'string') return JSON.parse(raw || '{}');
  return raw || {};
}

export function fail(res, e) {
  console.error(e);
  const setup = /token|store/i.test(String(e && e.message));
  res.status(setup ? 500 : 400).json({
    error: setup ? 'The results store isn’t connected. Create a private Blob store in Vercel and connect it to this project.'
                 : String(e && e.message || e),
  });
}
