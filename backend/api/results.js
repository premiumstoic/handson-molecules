// GET: every participant and session, for the admin page. Needs the admin key.

import { allResults } from '../lib/study.js';
import { defaultStore, fail, requireKey } from '../lib/http.js';

export function makeHandler(getStore = defaultStore) {
  return async function handler(req, res) {
    res.setHeader('Cache-Control', 'no-store');
    if (req.method !== 'GET') {
      res.setHeader('Allow', 'GET');
      return res.status(405).json({ error: 'Use GET.' });
    }
    if (!requireKey(req, res, 'ADMIN_KEY')) return;
    try {
      return res.status(200).json(await allResults(await getStore()));
    } catch (e) {
      return fail(res, e);
    }
  };
}

export default makeHandler();
