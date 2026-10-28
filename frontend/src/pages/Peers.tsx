import { api, EP, normPeer, toList } from '../api';
import { usePoll } from '../hooks';
import { Async, Badge, Card, Empty } from '../components/ui';

export default function Peers() {
  const s = usePoll(async () => toList(await api(EP.peers), ['peers', 'items', 'data']).map(normPeer));
  return (
    <Card title="Discovered peers">
      <Async s={s} what="peers" ep={EP.peers}>{(peers) => !peers.length
        ? <Empty title="No peers discovered" hint="Run another node on this LAN. Discovery is automatic." />
        : <div className="tw"><table><thead><tr><th>Peer</th><th>Address</th><th>Status</th><th>Latency</th><th>Last seen</th></tr></thead>
          <tbody>{peers.map((p) => <tr key={p.id}><td>{p.id}</td><td>{p.address}</td><td><Badge status={p.status} /></td>
            <td>{p.latency !== undefined ? `${p.latency} ms` : '—'}</td><td>{p.lastSeen ? String(p.lastSeen) : '—'}</td></tr>)}</tbody></table></div>}
      </Async>
    </Card>
  );
}
