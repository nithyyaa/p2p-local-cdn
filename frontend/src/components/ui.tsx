import { ReactNode } from 'react';
import { API_BASE } from '../api';
import { Poll } from '../hooks';

export const Card = ({ title, children }: { title?: string; children: ReactNode }) => (
  <section className="card">
    {title && <header className="card-h"><h3>{title}</h3></header>}
    {children}
  </section>
);

export const Stat = ({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) => (
  <div className="stat"><div className="stat-v">{value}</div><div className="stat-l">{label}</div>{hint && <div className="stat-hint">{hint}</div>}</div>
);

export const Badge = ({ status }: { status: string }) => {
  const s = status.toLowerCase();
  const kind = /fail|error|offline|down|dead|unreachable/.test(s) ? 'bad'
    : /online|active|ok|healthy|complete|done|up|connected/.test(s) ? 'good'
    : /pending|queue|connect|transfer|progress|running|stale|degraded/.test(s) ? 'warn' : 'idle';
  return <span className={`badge ${kind}`}><i />{status}</span>;
};

export const Spinner = ({ label = 'Loading…' }: { label?: string }) => <div className="state"><span className="spin" />{label}</div>;
export const Empty = ({ title, hint }: { title: string; hint?: string }) => <div className="state empty"><strong>{title}</strong>{hint && <span>{hint}</span>}</div>;

export function Async<T>({ s, what, ep, children }: { s: Poll<T>; what: string; ep: string; children: (d: T) => ReactNode }) {
  if (s.data === undefined) {
    if (s.loading) return <Spinner label={`Loading ${what}…`} />;
    if (s.error?.status === 404) return <Empty title={`${what} aren't available from the backend`} hint={`GET ${ep} returned 404. This view needs backend support, or set the matching VITE_EP_* variable in .env to your real route.`} />;
    return (
      <div className="state err"><strong>Couldn't load {what}</strong>
        <span>{s.error?.message}</span>
        <span>{s.error?.status === 0 ? `Check that the backend is running and CORS allows this origin (${API_BASE}).` : `GET ${ep}`}</span></div>
    );
  }
  return <>{s.error && <div className="warnbar">Showing last data. Refresh failed: {s.error.message}</div>}{children(s.data)}</>;
}

export const Kv = ({ obj }: { obj: any }) => {
  const rows = Object.entries(obj || {}).filter(([, v]) => v === null || typeof v !== 'object');
  if (!rows.length) return <Empty title="No node details returned" />;
  return <dl className="kv">{rows.map(([k, v]) => <div key={k}><dt>{k.replace(/_/g, ' ')}</dt><dd>{String(v)}</dd></div>)}</dl>;
};

export const Bar = ({ pct }: { pct?: number }) => (
  <div className="bar" title={pct === undefined ? 'unknown' : `${pct.toFixed(0)}%`}><div style={{ width: `${Math.max(0, Math.min(100, pct ?? 0))}%` }} /></div>
);
