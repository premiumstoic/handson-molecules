// POST: assign the next participant ID and its condition order.
// GET ?id=P07: that participant's record, so a second laptop can run their other condition.
// Both need the upload key the study laptops use.

import { assignParticipant, getParticipant } from '../lib/study.js';
import { body, defaultStore, fail, requireKey } from '../lib/http.js';

export function makeHandler(getStore = defaultStore) {
  return async function handler(req, res) {
    res.setHeader('Cache-Control', 'no-store');
    if (!requireKey(req, res, 'UPLOAD_KEY')) return;
    try {
      const store = await getStore();
      if (req.method === 'POST') return res.status(200).json(await assignParticipant(store, body(req).laptop));
      if (req.method === 'GET') {
        const found = await getParticipant(store, String(req.query?.id || ''));
        return found ? res.status(200).json(found) : res.status(404).json({ error: 'No such participant.' });
      }
      res.setHeader('Allow', 'GET, POST');
      return res.status(405).json({ error: 'Use GET or POST.' });
    } catch (e) {
      return fail(res, e);
    }
  };
}

export default makeHandler();
