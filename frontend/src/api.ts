
export class ApiError extends Error {
  status: number;
  constructor(m: string, s: number) {
    super(m);
    this.status = s;
  }
}

const env = import.meta.env;
const API_KEY = env.VITE_API_KEY || '';

export const API_BASE: string = (
  env.VITE_API_BASE_URL || `${location.protocol}//${location.hostname}:8000`
).replace(/\/$/, '');

export const POLL_MS: number = Number(env.VITE_POLL_INTERVAL_MS) || 5000;

export const EP = {
  health: env.VITE_EP_HEALTH || '/api/health',
  node: env.VITE_EP_NODE || '/api/health',
  peers: env.VITE_EP_PEERS || '/api/peers',
  stats: env.VITE_EP_STATS || '/api/stats',
  transfers: env.VITE_EP_TRANSFERS || '/api/transfers',
  cache: env.VITE_EP_CACHE || '/api/stats',
  bandwidth: env.VITE_EP_BANDWIDTH || '/api/bandwidth',
};


export async function api(
  path: string,
  options: RequestInit = {},
): Promise<any> {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), 8000);

  try {
    const r = await fetch(API_BASE + path, {
      ...options,
      signal: c.signal,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
        ...options.headers,
      },
    });

    if (!r.ok) {
      let detail = `HTTP ${r.status} ${r.statusText}`;

      try {
        const data = await r.json();
        detail = data.detail || detail;
      } catch {
        // Keep the original HTTP error if the response isn't JSON.
      }

      throw new ApiError(detail, r.status);
    }

    return await r.json();
  } catch (e: any) {
    if (e instanceof ApiError) throw e;

    throw new ApiError(
      e?.name === 'AbortError'
        ? 'Request timed out'
        : `Cannot reach backend at ${API_BASE}`,
      0,
    );
  } finally {
    clearTimeout(t);
  }
}


export const pick = (o: any, keys: string[], d: any = undefined) => {
  for (const k of keys) {
    if (o && o[k] !== undefined && o[k] !== null) return o[k];
  }
  return d;
};

export function toList(d: any, keys: string[]): any[] {
  if (Array.isArray(d)) return d;

  for (const k of keys) {
    if (Array.isArray(d?.[k])) return d[k];
  }

  if (d && typeof d === 'object') {
    const e = Object.entries(d);

    if (
      e.length &&
      e.every(([, v]) => v && typeof v === 'object' && !Array.isArray(v))
    ) {
      return e.map(([k, v]: any) => ({ id: k, ...v }));
    }
  }

  return [];
}

export interface Peer {
  id: string;
  address: string;
  status: string;
  latency?: number;
  lastSeen?: string;
  raw: any;
}

export interface Transfer {
  id: string;
  name: string;
  peer: string;
  status: string;
  progress?: number;
  bytes?: number;
  speed?: number;
  raw: any;
}

export const normPeer = (p: any, i: number): Peer => ({
  id: String(pick(p, ['id', 'peer_id', 'node_id', 'name'], `peer-${i + 1}`)),
  address:
    [
      pick(p, ['host', 'ip', 'address', 'addr'], ''),
      pick(p, ['port'], ''),
    ]
      .filter((x) => x !== '')
      .join(':') || '—',
  status: String(
    pick(p, ['status', 'state'], p?.online === false ? 'offline' : 'online'),
  ).toLowerCase(),
  latency: pick(p, ['latency_ms', 'latency', 'rtt_ms']),
  lastSeen: pick(p, ['last_seen', 'lastSeen', 'updated_at']),
  raw: p,
});

export const normTransfer = (t: any, i: number): Transfer => {
  let prog = pick(t, ['progress', 'percent', 'pct']);

  if (prog === undefined && t?.bytes_done !== undefined && t?.bytes_total) {
    prog = (t.bytes_done / t.bytes_total) * 100;
  }

  if (typeof prog === 'number' && prog <= 1 && prog > 0) {
    prog *= 100;
  }

  return {
    id: String(pick(t, ['id', 'transfer_id', 'hash'], `t-${i + 1}`)),
    name: String(
      pick(t, ['file', 'filename', 'name', 'path', 'content_id', 'hash'], '—'),
    ),
    peer: String(pick(t, ['peer', 'peer_id', 'source', 'node_id'], '—')),
    status: String(pick(t, ['status', 'state'], 'unknown')).toLowerCase(),
    progress: prog,
    bytes: pick(t, ['bytes', 'size', 'size_bytes', 'bytes_total']),
    speed: pick(t, ['speed', 'speed_bps', 'rate_bps', 'throughput']),
    raw: t,
  };
};

export const fmtBytes = (n?: number) => {
  if (typeof n !== 'number' || isNaN(n)) return '—';

  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;

  while (n >= 1024 && i < u.length - 1) {
    n /= 1024;
    i++;
  }

  return `${n.toFixed(i ? 1 : 0)} ${u[i]}`;
};

export const fmtUptime = (sec?: number) => {
  if (typeof sec !== 'number' || isNaN(sec)) return undefined;

  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  const m = Math.floor((sec % 3600) / 60);

  return d
    ? `${d}d ${h}h ${m}m`
    : h
      ? `${h}h ${m}m`
      : m
        ? `${m}m ${Math.floor(sec % 60)}s`
        : `${Math.floor(sec)}s`;
};
