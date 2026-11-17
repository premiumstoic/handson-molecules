import { test } from 'node:test';
import assert from 'node:assert/strict';
import { memoryStore } from '../lib/store.js';
import { allResults, assignParticipant, cleanSession, conditionOrder, getParticipant, saveSession } from '../lib/study.js';
import { makeHandler as participants } from '../api/participants.js';

test('odd IDs start with gestures, even IDs with the mouse', () => {
  assert.deepEqual(conditionOrder(1), ['gesture', 'mouse']);
  assert.deepEqual(conditionOrder(2), ['mouse', 'gesture']);
});

test('IDs count up and never repeat, even when asked at the same time', async () => {
  const store = memoryStore();
  const first = await assignParticipant(store, 'laptop-a');
  assert.equal(first.id, 'P01');
  assert.deepEqual(first.order, ['gesture', 'mouse']);
  const many = await Promise.all([1, 2, 3, 4].map(() => assignParticipant(store)));
  assert.deepEqual(many.map(p => p.id).sort(), ['P02', 'P03', 'P04', 'P05']);
  assert.deepEqual((await getParticipant(store, 'P02')).order, ['mouse', 'gesture']);
  assert.equal(await getParticipant(store, '../secret'), null);
});

test('sessions keep only known fields and are overwritten as tasks finish', async () => {
  const store = memoryStore();
  const base = { participant: 'P01', condition: 'gesture', session_id: 'abc12345', laptop: 'laptop-a',
                 hostname: 'Ahmets-MacBook', camera: { width: 1280, height: 720, fps: 30 } };
  await saveSession(store, { ...base, tasks: [{ task: 1, molecule: 'caffeine', outcome: 'done', seconds: 5.2 }] });
  await saveSession(store, { ...base, finished: true, tasks: [{ task: 1, molecule: 'caffeine', outcome: 'done', seconds: 5.2 },
                                                              { task: 2, molecule: 'caffeine', outcome: 'odd', seconds: 9 }] });
  const { sessions } = await allResults(store);
  assert.equal(sessions.length, 1);
  assert.equal(sessions[0].finished, true);
  assert.equal(sessions[0].tasks[1].outcome, 'skipped');
  assert.equal('hostname' in sessions[0], false);
});

test('bad records are refused', () => {
  assert.throws(() => cleanSession({ participant: 'Ahmet', condition: 'gesture', session_id: 'abc12345' }));
  assert.throws(() => cleanSession({ participant: 'P01', condition: 'keyboard', session_id: 'abc12345' }));
  assert.doesNotThrow(() => cleanSession({ participant: 'laptop-a-L3', condition: 'mouse', session_id: 'abc12345' }));
});

test('the API needs the upload key', async () => {
  process.env.UPLOAD_KEY = 'secret';
  const store = memoryStore();
  const handler = participants(async () => store);
  const call = async auth => {
    const res = { headers: {}, setHeader(k, v) { this.headers[k] = v; }, status(c) { this.code = c; return this; },
                  json(v) { this.body = v; } };
    await handler({ method: 'POST', headers: { authorization: auth }, body: '{}' }, res);
    return res;
  };
  assert.equal((await call('Bearer wrong')).code, 401);
  const ok = await call('Bearer secret');
  assert.equal(ok.code, 200);
  assert.equal(ok.body.id, 'P01');
});
