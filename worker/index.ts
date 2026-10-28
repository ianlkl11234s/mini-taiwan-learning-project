// mini-taiwan-learning-project 的 Cloudflare Worker：tracks_od_bundle.json（41.6MiB）從 R2 提供。
// 只處理超過 Workers 靜態資產單檔 25MiB 上限的大檔（放在 R2 bucket site-assets），其餘交回靜態資產。
// 支援 GET／HEAD、Range（206）、If-None-Match（304）；寫法同 plan-art 的 worker/index.ts。

interface R2ObjectLike {
  httpEtag: string;
  size: number;
  range?: { offset?: number; length?: number; suffix?: number };
  writeHttpMetadata(headers: Headers): void;
}
interface R2ObjectBodyLike extends R2ObjectLike {
  body: ReadableStream;
}
interface Env {
  ASSETS: { fetch(request: Request): Promise<Response> };
  BIG: {
    get(
      key: string,
      options?: { range?: Headers; onlyIf?: Headers },
    ): Promise<R2ObjectBodyLike | R2ObjectLike | null>;
    head(key: string): Promise<R2ObjectLike | null>;
  };
}

// 網站路徑 → R2 key（規則：<站名>/<路徑去掉開頭 />）。新增大檔時兩邊都要加，並同步 wrangler.jsonc 的 run_worker_first
const BIG_FILES: Record<string, string> = {
  "/data/tra/tracks_od/tracks_od_bundle.json": "mini-taiwan-learning-project/data/tra/tracks_od/tracks_od_bundle.json",
};

// R2 物件的 content-type 不一定可靠，一律依副檔名覆寫
const CONTENT_TYPES: Record<string, string> = {
  json: "application/json",
};

async function serveBig(request: Request, env: Env, key: string): Promise<Response> {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Method Not Allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
  }
  const object =
    request.method === "HEAD"
      ? await env.BIG.head(key)
      : await env.BIG.get(key, { range: request.headers, onlyIf: request.headers });
  if (!object) return new Response("Not Found", { status: 404 });

  const headers = new Headers();
  object.writeHttpMetadata(headers);
  const ext = key.split(".").pop()?.toLowerCase() ?? "";
  if (CONTENT_TYPES[ext]) headers.set("Content-Type", CONTENT_TYPES[ext]);
  headers.set("ETag", object.httpEtag);
  headers.set("Accept-Ranges", "bytes");
  // 檔名不帶 hash：短快取，更新檔案後 1 小時內生效
  headers.set("Cache-Control", "public, max-age=3600");

  if (request.method === "HEAD") {
    headers.set("Content-Length", String(object.size));
    return new Response(null, { headers });
  }
  // onlyIf 條件不成立（If-None-Match 命中）時 R2 回不帶 body 的物件
  if (!("body" in object)) return new Response(null, { status: 304, headers });

  if (object.range && request.headers.has("Range")) {
    const { offset = 0, length = object.size - offset } = object.range;
    headers.set("Content-Range", `bytes ${offset}-${offset + length - 1}/${object.size}`);
    headers.set("Content-Length", String(length));
    return new Response(object.body, { status: 206, headers });
  }
  return new Response(object.body, { headers });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const key = BIG_FILES[new URL(request.url).pathname];
    if (key) return serveBig(request, env, key);
    return env.ASSETS.fetch(request);
  },
};
