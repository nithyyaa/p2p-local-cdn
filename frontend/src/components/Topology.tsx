import { Peer } from '../api';
import { Empty } from './ui';

export default function Topology({ peers, selfId }: { peers: Peer[]; selfId: string }) {
  if (!peers.length) return <Empty title="No peers discovered yet" hint="Start another node on the same network; it appears here once the backend reports it." />;
  const W = 640, H = 380, cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2 - 50;
  const shown = peers.slice(0, 40);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="topo" role="img" aria-label="Network topology">
      {shown.map((p, i) => {
        const a = (i / shown.length) * Math.PI * 2 - Math.PI / 2;
        const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
        const off = /off|down|dead|fail|unreach/.test(p.status);
        return (
          <g key={p.id}>
            <line x1={cx} y1={cy} x2={x} y2={y} className={off ? 'edge off' : 'edge'} />
            <circle cx={x} cy={y} r={12} className={off ? 'node off' : 'node'}><title>{`${p.id}\n${p.address}\n${p.status}${p.latency !== undefined ? `\n${p.latency} ms` : ''}`}</title></circle>
            <text x={x} y={y + 27} textAnchor="middle" className="nl">{p.id.length > 12 ? p.id.slice(0, 11) + '…' : p.id}</text>
          </g>
        );
      })}
      <circle cx={cx} cy={cy} r={20} className="node self" />
      <text x={cx} y={cy + 38} textAnchor="middle" className="nl">{selfId}</text>
      {peers.length > shown.length && <text x={10} y={H - 10} className="nl">+{peers.length - shown.length} more peers not drawn</text>}
    </svg>
  );
}
