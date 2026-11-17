// POST: save (or update) one study session; the app sends the whole record after every task.

import { saveSession } from '../lib/study.js';
import { body, defaultStore, fail, requireKey } from '../lib/http.js';

export function makeHandler(getStore = defaultStore) {
  return async function handler(req, res) {
    res.setHeader('Cache-Control', 'no-store');
    if (req.method !== 'POST') {
      res.setHeader('Allow', 'POST');
      return res.status(405).json({ error: 'Use POST.' });
    }
    if (!requireKey(req, res, 'UPLOAD_KEY')) return;
    try {
      const saved = await saveSession(await getStore(), body(req));
      return res.status(200).json({ ok: true, received: saved.received });
    } catch (e) {
      return fail(res, e);
    }
  };
}

export default makeHandler();
