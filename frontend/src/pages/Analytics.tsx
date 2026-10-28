import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, EP, fmtBytes, pick, toList } from '../api';
import { usePoll } from '../hooks';
import { Async, Card, Empty, Stat } from '../components/ui';

const tip = { background: 'var(--panel)', border: '1px solid var(--line)' };

export default function Analytics() {
  const cache = usePoll(() => api(EP.cache));
  const bw = usePoll(() => api(EP.bandwidth));
  return (
    <>
      <Card title="Cache">
        <Async s={cache} what="cache stats" ep={EP.cache}>{(c) => {
          const hits = pick(c, ['hits', 'cache_hits']), misses = pick(c, ['misses', 'cache_misses']);
          const used = pick(c, ['cached_bytes', 'size_bytes', 'used_bytes', 'size']), cap = pick(c, ['capacity_bytes', 'max_bytes', 'capacity']);
          const items = pick(c, ['cached_chunks', 'items', 'entries', 'count', 'objects']);
          const total = typeof hits === 'number' && typeof misses === 'number' ? hits + misses : undefined;
          return (
            <>
              <div className="grid stats">
                <Stat label="Hit rate" value={total ? `${((hits / total) * 100).toFixed(1)}%` : '—'} hint={total === 0 ? 'No requests yet' : undefined} />
                <Stat label="Cached items" value={items ?? '—'} />
                <Stat label="Storage used" value={fmtBytes(used)} hint={typeof cap === 'number' ? `of ${fmtBytes(cap)}` : undefined} />
              </div>
              {total ? <div className="chart"><ResponsiveContainer width="100%" height={200}>
                <BarChart data={[{ name: 'Hits', v: hits }, { name: 'Misses', v: misses }]}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                  <XAxis dataKey="name" stroke="var(--mute)" /><YAxis stroke="var(--mute)" allowDecimals={false} />
                  <Tooltip contentStyle={tip} /><Bar dataKey="v" fill="var(--accent)" radius={[4, 4, 0, 0]} /></BarChart>
              </ResponsiveContainer></div> : <Empty title="No cache requests recorded" hint="Hit and miss charts need the backend to report `hits` and `misses` counters." />}
            </>);
        }}</Async>
      </Card>
      <Card title="Bandwidth">
        <Async s={bw} what="bandwidth analytics" ep={EP.bandwidth}>{(b) => {
          const saved = pick(b, ['bytes_saved', 'saved_bytes', 'saved']);
          const peer = pick(b, ['bytes_from_peers', 'peer_bytes']), origin = pick(b, ['bytes_from_origin', 'origin_bytes']);
          const series = toList(b, ['series', 'history', 'samples']).map((x: any) => ({
            t: String(pick(x, ['t', 'time', 'timestamp'], '')), peer: pick(x, ['peer', 'peer_bytes', 'bytes_from_peers'], 0), origin: pick(x, ['origin', 'origin_bytes', 'bytes_from_origin'], 0) }));
          return (
            <>
              <div className="grid stats">
                <Stat label="Bandwidth saved" value={fmtBytes(saved)} />
                <Stat label="Served by peers" value={fmtBytes(peer)} />
                <Stat label="Fetched from origin" value={fmtBytes(origin)} />
              </div>
              {series.length ? <div className="chart"><ResponsiveContainer width="100%" height={240}>
                <AreaChart data={series}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" /><XAxis dataKey="t" stroke="var(--mute)" /><YAxis stroke="var(--mute)" tickFormatter={(v) => fmtBytes(v)} />
                  <Tooltip formatter={(v: any) => fmtBytes(Number(v))} contentStyle={tip} />
                  <Area dataKey="peer" name="Peers" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.25} />
                  <Area dataKey="origin" name="Origin" stroke="var(--warn)" fill="var(--warn)" fillOpacity={0.2} /></AreaChart>
              </ResponsiveContainer></div> : <Empty title="No time-series data" hint="A bandwidth history chart needs the backend to return a `series` array of {t, peer, origin} samples." />}
            </>);
        }}</Async>
      </Card>
    </>
  );
}
