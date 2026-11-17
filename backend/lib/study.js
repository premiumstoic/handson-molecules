// Study records: participant IDs with their condition order, and one record per session.
// Pure logic over a store (see store.js), so it can be tested without Vercel.

import { ExistsError } from './store.js';

export const CONDITIONS = ['gesture', 'mouse'];
const ID = /^P\d{2,4}$/;
const LOCAL_ID = /^[a-z0-9-]{1,24}-L\d{1,4}$/;      // offline fallback from the app, e.g. laptop-a-L3
const SESSION_ID = /^[A-Za-z0-9-]{8,64}$/;
const TEXT_FIELDS = { laptop: 40, app_version: 40, os: 120, python: 40, started: 40, finished_at: 40 };
const OUTCOMES = ['done', 'timeout', 'skipped'];

// Odd numbers start with gestures, even numbers with the mouse, so learning effects even out.
export function conditionOrder(number) {
  return number % 2 === 1 ? ['gesture', 'mouse'] : ['mouse', 'gesture'];
}

export async function assignParticipant(store, laptop = '') {
  const taken = (await store.list('participants/'))
    .map(p => Number(p.match(/participants\/P(\d+)\.json$/)?.[1]))
    .filter(Number.isFinite);
  let number = Math.max(0, ...taken) + 1;
  // create() refuses an existing file, so two laptops asking at once never get the same ID.
  for (let attempt = 0; attempt < 10; attempt++, number++) {
    const id = `P${String(number).padStart(2, '0')}`;
    const record = { id, number, order: conditionOrder(number), created: new Date().toISOString(),
                     laptop: String(laptop).slice(0, 40) };
    try {
      await store.create(`participants/${id}.json`, record);
      return record;
    } catch (e) {
      if (!(e instanceof ExistsError)) throw e;
    }
  }
  throw new Error('Could not assign a participant ID; try again.');
}

export async function getParticipant(store, id) {
  if (!ID.test(id)) return null;
  return store.get(`participants/${id}.json`);
}

// Keep only known fields with sane types, so the store never holds anything unexpected.
export function cleanSession(body) {
  if (!body || typeof body !== 'object') throw new Error('Send a session record.');
  const participant = String(body.participant || '');
  if (!ID.test(participant) && !LOCAL_ID.test(participant)) throw new Error('Unknown participant ID format.');
  if (!CONDITIONS.includes(body.condition)) throw new Error('Unknown condition.');
  if (!SESSION_ID.test(String(body.session_id || ''))) throw new Error('Missing session_id.');
  const out = { participant, condition: body.condition, session_id: body.session_id, finished: body.finished === true };
  for (const [key, max] of Object.entries(TEXT_FIELDS)) {
    if (typeof body[key] === 'string') out[key] = body[key].slice(0, max);
  }
  const num = v => (typeof v === 'number' && Number.isFinite(v) ? v : null);
  if (body.camera && typeof body.camera === 'object') {
    out.camera = { width: num(body.camera.width), height: num(body.camera.height), fps: num(body.camera.fps) };
  }
  if (body.screen && typeof body.screen === 'object') {
    out.screen = { width: num(body.screen.width), height: num(body.screen.height) };
  }
  out.tasks = (Array.isArray(body.tasks) ? body.tasks : []).slice(0, 50).map(t => ({
    task: num(t.task), molecule: String(t.molecule || '').slice(0, 30),
    outcome: OUTCOMES.includes(t.outcome) ? t.outcome : 'skipped',
    seconds: num(t.seconds), false_triggers: num(t.false_triggers) ?? 0,
  }));
  return out;
}

export async function saveSession(store, body) {
  const session = cleanSession(body);
  session.received = new Date().toISOString();
  // Overwritten as the session goes on: the app sends the whole record after every task.
  await store.put(`sessions/${session.participant}-${session.condition}-${session.session_id}.json`, session);
  return session;
}

export async function allResults(store) {
  const read = async prefix => (await Promise.all((await store.list(prefix)).map(p => store.get(p)))).filter(Boolean);
  return { participants: await read('participants/'), sessions: await read('sessions/') };
}
