import { Peer } from '../api';
import { IconRadar } from './icons';

const MAX = 24;
export default function NetworkMap({ peers, selfName }: { peers: Peer[]; selfName: string }) {
  const W = 700, H = peers.length ? 380 : 190, cx = W / 2, cy = H / 2, R = 135;
  const shown = peers.slice(0, MAX);
  const label = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} className="map" role="img" aria-label={`Network map: this node and ${peers.length} discovered peers`}>
        {shown.map((p, i) => {
          const a = (i / shown.length) * Math.PI * 2 - Math.PI / 2;
          const x = cx + R * 1.5 * Math.cos(a), y = cy + R * Math.sin(a);
          const off = /off|down|dead|fail|unreach/.test(p.status);
          return (
            <g key={p.id}>
              <line x1={cx} y1={cy} x2={x} y2={y} className={off ? 'edge off' : 'edge'} />
              <circle cx={x} cy={y} r={7} className={off ? 'peer off' : 'peer'}><title>{`${p.id}\n${p.address}\n${p.status}${p.latency !== undefined ? `\n${p.latency} ms` : ''}`}</title></circle>
              <text x={x} y={y + 22} textAnchor="middle" className="t1">{label(p.id, 14)}</text>
              {p.address !== '—' && <text x={x} y={y + 35} textAnchor="middle">{label(p.address, 22)}</text>}
            </g>
          );
        })}
        <rect x={cx - 17} y={cy - 17} width={34} height={34} rx={7} className="me" />
        <circle cx={cx} cy={cy} r={4} fill="var(--accent)" />
        <text x={cx} y={cy + 36} textAnchor="middle" className="t1">{label(selfName, 24)}</text>
        <text x={cx} y={cy + 49} textAnchor="middle">this node</text>
      </svg>
      {peers.length > MAX && <div className="legend">+{peers.length - MAX} more peers are listed on the Peers page</div>}
      {peers.length > 0 && <div className="legend"><span><i />Discovered on the LAN</span><span><i className="o" />Reported offline</span></div>}
      {peers.length === 0 && (
        <div className="ov-empty"><IconRadar /><div><strong>No peers discovered yet</strong>
          Start Peerlight on another device on this network. Discovery needs no configuration, and the peer appears here as soon as it announces itself.</div></div>
      )}
    </>
  );
}
