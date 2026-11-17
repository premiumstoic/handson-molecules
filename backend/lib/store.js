// Where records live. blobStore is the real one (a private Vercel Blob store, one JSON file per
// record); memoryStore is for tests and the local dev server.

export class ExistsError extends Error {}

export function memoryStore() {
  const files = new Map();
  return {
    async create(path, value) {
      if (files.has(path)) throw new ExistsError(path);
      files.set(path, JSON.stringify(value));
    },
    async put(path, value) {
      files.set(path, JSON.stringify(value));
    },
    async list(prefix) {
      return [...files.keys()].filter(p => p.startsWith(prefix)).sort();
    },
    async get(path) {
      return files.has(path) ? JSON.parse(files.get(path)) : null;
    },
  };
}

export async function blobStore() {
  const { put, list, get } = await import('@vercel/blob');
  const write = (path, value, allowOverwrite) => put(path, JSON.stringify(value), {
    access: 'private', addRandomSuffix: false, allowOverwrite, contentType: 'application/json',
  });
  return {
    async create(path, value) {
      try {
        await write(path, value, false);
      } catch (e) {
        if (/already exists/i.test(String(e && e.message))) throw new ExistsError(path);
        throw e;
      }
    },
    async put(path, value) {
      await write(path, value, true);
    },
    async list(prefix) {
      const paths = [];
      let cursor;
      do {
        const page = await list({ prefix, cursor, limit: 1000 });
        paths.push(...page.blobs.map(b => b.pathname));
        cursor = page.hasMore ? page.cursor : undefined;
      } while (cursor);
      return paths.sort();
    },
    async get(path) {
      const got = await get(path, { access: 'private', useCache: false });
      if (!got || !got.stream) return null;
      return JSON.parse(await new Response(got.stream).text());
    },
  };
}
