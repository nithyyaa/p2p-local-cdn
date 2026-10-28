import { ReactNode } from 'react';
import { api, API_BASE, EP, fmtBytes, fmtUptime, normPeer, pick, toList } from '../api';
import { usePoll } from '../hooks';
import { Async } from '../components/ui';
import NetworkMap from '../components/NetworkMap';
import { IconDisk, IconLog, IconPeers, IconPulse, IconSwap, Mark } from '../components/icons';

const Metric = ({ icon, label, value, sub, tone }: { icon: ReactNode; label: string; value: ReactNode; sub?: string; tone?: string }) => (
  <div className="metric"><div className="metric-l">{icon}{label}</div><div className={`metric-v ${tone || ''}`}>{value}</div>{sub && <div className="metric-s">{sub}</div>}</div>
);

const Panel = ({ title, meta, children }: { title: string; meta?: string; children: ReactNode }) => (
  <section className="panel"><header className="panel-h"><h2>{title}</h2>{meta && <span>{meta}</span>}</header><div className="panel-b">{children}</div></section>
);

const Row = ({ k, v }: { k: string; v: unknown }) => {
  const has = v !== undefined && v !== null && v !== '';
  return <div><dt>{k}</dt><dd className={has ? '' : 'na'}>{has ? String(v) : 'Not reported'}</dd></div>;
};

export default function Overview() {
  const health = usePoll(() => api(EP.health));
  const stats = usePoll(() => api(EP.stats));
  const peersP = usePoll(async () => {
    const d = await api(EP.peers);
    const peers = toList(d, ['peers', 'items', 'data']).map(normPeer);
    return { count: typeof d?.peer_count === 'number' ? d.peer_count : peers.length, peers };
  });
  const xfer = usePoll(async () => toList(await api(EP.transfers), ['transfers', 'items', 'data']));

  const h = health.data, st = stats.data;
  const conn = h ? 'up' : health.loading ? 'checking' : 'down';
  const apiStatus = h ? String(pick(h, ['status', 'state'], 'ok')) : undefined;
  const selfName = String(pick(h, ['node_name', 'name', 'hostname'], 'This node'));
  const uptime = fmtUptime(pick(st, ['uptime_seconds']) ?? pick(h, ['uptime_seconds', 'uptime']));
  const activeXfer = xfer.data?.filter((t) => /active|progress|running|transfer|pending/.test(String(pick(t, ['status', 'state'], '')).toLowerCase())).length;
  const updated = health.updated ? new Date(health.updated).toLocaleTimeString() : undefined;

  return (
    <div className="ov">
      <header className="ov-head">
        <div className="ov-title"><span className="ov-mark"><Mark /></span>
          <div><h1>Overview</h1><small>Peerlight · network observability</small></div></div>
        <div className={`conn ${conn}`} role="status">
          <i />{conn === 'up' ? 'Connected' : conn === 'checking' ? 'Connecting…' : health.error?.status === 0 ? 'Backend unreachable' : `Backend error (${health.error?.message})`}
          <span>{conn === 'up' && updated ? `updated ${updated}` : API_BASE}</span>
        </div>
      </header>

      <div className="ov-metrics">
        <Metric icon={<IconPulse />} label="Backend status" value={apiStatus ?? (health.loading ? '…' : 'Offline')} tone={h ? 'good' : health.loading ? '' : 'bad'} sub={h ? `${EP.health}` : health.error?.message} />
        <Metric icon={<IconPeers />} label="Discovered peers" value={peersP.data ? peersP.data.count : peersP.loading ? '…' : '—'} sub={peersP.error && !peersP.data ? 'Peer list unavailable' : 'On the local network'} />
        <Metric icon={<IconDisk />} label="Cached storage" value={st ? fmtBytes(pick(st, ['cached_bytes'])) : stats.loading ? '…' : '—'}
          sub={st ? `${pick(st, ['cached_chunks'], 0)} chunks` : stats.error ? 'Stats unavailable' : undefined} />
        {xfer.data !== undefined && <Metric icon={<IconSwap />} label="Active transfers" value={activeXfer ?? 0} sub={`${xfer.data.length} reported`} />}
      </div>

      <div className="ov-grid">
        <Panel title="Network" meta={peersP.data ? `${peersP.data.peers.length} peer${peersP.data.peers.length === 1 ? '' : 's'} listed` : undefined}>
          <Async s={peersP} what="peers" ep={EP.peers}>{(d) => <NetworkMap peers={d.peers} selfName={selfName} />}</Async>
        </Panel>

        <Panel title="Node information">
          {h === undefined && health.loading ? <div style={{ display: 'grid', gap: '.8rem' }}>{[0, 1, 2, 3, 4].map((i) => <div key={i} className="skel" />)}</div> : (
            <Async s={health} what="node info" ep={EP.health}>{(n) => (
              <dl className="info">
                <Row k="Node name" v={pick(n, ['node_name', 'name'])} />
                <Row k="Node ID" v={pick(n, ['node_id', 'id', 'peer_id'])} />
                <Row k="Hostname" v={pick(n, ['hostname', 'host'])} />
                <Row k="LAN IPv4" v={pick(n, ['lan_ip', 'lan_ipv4', 'ipv4', 'ip', 'ip_address', 'address'])} />
                <Row k="API status" v={apiStatus} />
                <Row k="Uptime" v={uptime} />
                <Row k="Transfer port" v={pick(n, ['transfer_port', 'tcp_port', 'port'])} />
                <Row k="Discovery port" v={pick(n, ['discovery_port', 'udp_port', 'mdns_port'])} />
              </dl>)}</Async>
          )}
        </Panel>
      </div>

      <Panel title="Recent activity">
        <div className="ov-empty"><IconLog /><div><strong>No activity feed available</strong>
          The backend doesn't expose an event log or transfer history yet, so nothing is shown here rather than guessing. Once an events endpoint exists, genuine peer and transfer events will appear in this panel.</div></div>
      </Panel>
    </div>
  );
}
