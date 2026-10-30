
import { ReactNode, useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  api,
  API_BASE,
  EP,
  fmtBytes,
  fmtUptime,
  normPeer,
  pick,
  toList,
} from '../api';

import { usePoll } from '../hooks';
import { Async } from '../components/ui';
import NetworkMap from '../components/NetworkMap';
import {
  IconDisk,
  IconLog,
  IconPeers,
  IconPulse,
  IconSwap,
  Mark,
} from '../components/icons';

const Metric = ({
  icon,
  label,
  value,
  sub,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  sub?: string;
  tone?: string;
}) => (
  <div className="metric">
    <div className="metric-l">
      {icon}
      {label}
    </div>
    <div className={`metric-v ${tone || ''}`}>{value}</div>
    {sub && <div className="metric-s">{sub}</div>}
  </div>
);

const Panel = ({
  title,
  meta,
  children,
}: {
  title: string;
  meta?: string;
  children: ReactNode;
}) => (
  <section className="panel">
    <header className="panel-h">
      <h2>{title}</h2>
      {meta && <span>{meta}</span>}
    </header>
    <div className="panel-b">{children}</div>
  </section>
);

const Row = ({ k, v }: { k: string; v: unknown }) => {
  const has = v !== undefined && v !== null && v !== '';

  return (
    <div>
      <dt>{k}</dt>
      <dd className={has ? '' : 'na'}>
        {has ? String(v) : 'Not reported'}
      </dd>
    </div>
  );
};

type TrafficPoint = {
  time: string;
  bytesPerSecond: number;
};

const chartTooltipStyle = {
  background: 'var(--panel)',
  border: '1px solid var(--line)',
  borderRadius: 8,
};

export default function Overview() {
  const health = usePoll(() => api(EP.health));
  const stats = usePoll(() => api(EP.stats));

  const peersP = usePoll(async () => {
    const d = await api(EP.peers);
    const peers = toList(d, ['peers', 'items', 'data']).map(normPeer);

    return {
      count:
        typeof d?.peer_count === 'number' ? d.peer_count : peers.length,
      peers,
    };
  });

  const xfer = usePoll(async () =>
    toList(await api(EP.transfers), ['transfers', 'items', 'data']),
  );

  const [traffic, setTraffic] = useState<TrafficPoint[]>([]);
  const [trafficAvailable, setTrafficAvailable] = useState(false);

  useEffect(() => {
    let previousTotal: number | undefined;
    let previousTime: number | undefined;
    let disposed = false;

    const sample = async () => {
      try {
        const data = await api(EP.stats);
        if (disposed) return;

        const metrics = pick(data, ['transfer_metrics'], {});
        const total = Number(
          pick(metrics, ['total_transferred_bytes'], undefined) ??
          pick(data, ['total_transferred_bytes'], 0),
        );
        const now = Date.now();

        if (Number.isFinite(total)) {
          setTrafficAvailable(true);

          if (previousTotal !== undefined && previousTime !== undefined) {
            const elapsed = (now - previousTime) / 1000;
            const delta = total - previousTotal;

            // Ignore negative deltas if the backend restarted or counters reset.
            const rate =
              elapsed > 0 && delta >= 0 ? delta / elapsed : 0;

            setTraffic((old) =>
              [
                ...old,
                {
                  time: new Date(now).toLocaleTimeString([], {
                    minute: '2-digit',
                    second: '2-digit',
                  }),
                  bytesPerSecond: Math.round(rate),
                },
              ].slice(-20),
            );
          }

          previousTotal = total;
          previousTime = now;
        }
      } catch {
        // Other dashboard panels show API errors. Keep the chart usable.
      }
    };

    void sample();

    const timer = window.setInterval(() => {
      void sample();
    }, 3000);

    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, []);

  const h = health.data;
  const st = stats.data;

  const conn = h ? 'up' : health.loading ? 'checking' : 'down';

  const apiStatus = h
    ? String(pick(h, ['status', 'state'], 'ok'))
    : undefined;

  const selfName = String(
    pick(h, ['node_name', 'name', 'hostname'], 'This node'),
  );

  const uptime = fmtUptime(
    pick(st, ['uptime_seconds']) ??
      pick(h, ['uptime_seconds', 'uptime']),
  );

  const activeXfer =
    xfer.data?.filter((t) =>
      /active|progress|running|pending/.test(
        String(pick(t, ['status', 'state'], '')).toLowerCase(),
      ),
    ).length ?? 0;

  const updated = health.updated
    ? new Date(health.updated).toLocaleTimeString()
    : undefined;

  const metrics = pick(st, ['transfer_metrics'], {});

  const totalTransfers = Number(pick(metrics, ['total_transfers'], 0));
  const completedTransfers = Number(
    pick(metrics, ['completed_transfers'], 0),
  );
  const failedTransfers = Number(pick(metrics, ['failed_transfers'], 0));
  const peerBytes = Number(pick(metrics, ['peer_bytes'], 0));
  const originBytes = Number(pick(metrics, ['origin_bytes'], 0));
  const cacheBytes = Number(pick(metrics, ['cache_bytes'], 0));

  const savedBytes = Number(
    pick(metrics, ['estimated_origin_bytes_saved'], 0),
  );

  const totalTraffic = peerBytes + originBytes + cacheBytes;

  const latestRate =
    traffic.length > 0
      ? traffic[traffic.length - 1].bytesPerSecond
      : 0;

  const recentTransfers = [...(xfer.data ?? [])].slice(-5).reverse();

  return (
    <div className="ov">
      <header className="ov-head">
        <div className="ov-title">
          <span className="ov-mark">
            <Mark />
          </span>
          <div>
            <h1>Network Overview</h1>
            <small>Peerlight · peer-to-peer network observability</small>
          </div>
        </div>

        <div className={`conn ${conn}`} role="status">
          <i />
          {conn === 'up'
            ? 'Backend connected'
            : conn === 'checking'
              ? 'Connecting...'
              : health.error?.status === 0
                ? 'Backend unreachable'
                : `Backend error (${health.error?.message ?? 'unknown'})`}
          <span>
            {conn === 'up' && updated ? `Updated ${updated}` : API_BASE}
          </span>
        </div>
      </header>

      <div className="ov-metrics">
        <Metric
          icon={<IconPulse />}
          label="Backend status"
          value={apiStatus ?? (health.loading ? 'Checking...' : 'Offline')}
          tone={h ? 'good' : health.loading ? '' : 'bad'}
          sub={h ? 'API responding' : health.error?.message}
        />

        <Metric
          icon={<IconPeers />}
          label="Discovered peers"
          value={
            peersP.data
              ? peersP.data.count
              : peersP.loading
                ? '...'
                : '—'
          }
          sub="Peers reported by this node"
        />

        <Metric
          icon={<IconDisk />}
          label="Cached storage"
          value={
            st ? fmtBytes(Number(pick(st, ['cached_bytes'], 0))) : '...'
          }
          sub={`${pick(st, ['cached_chunks'], 0)} cached chunks`}
        />

        <Metric
          icon={<IconSwap />}
          label="Active transfers"
          value={activeXfer}
          sub={`${xfer.data?.length ?? 0} records returned`}
        />
      </div>

      <div className="ov-grid">
        <Panel
          title="Network topology"
          meta={
            peersP.data
              ? `${peersP.data.peers.length} peer${peersP.data.peers.length === 1 ? '' : 's'} listed`
              : 'Discovering peers'
          }
        >
          <Async s={peersP} what="peers" ep={EP.peers}>
            {(d) => <NetworkMap peers={d.peers} selfName={selfName} />}
          </Async>
        </Panel>

        <Panel title="This node">
          {h === undefined && health.loading ? (
            <div style={{ display: 'grid', gap: '.8rem' }}>
              {[0, 1, 2, 3, 4].map((i) => (
                <div key={i} className="skel" />
              ))}
            </div>
          ) : (
            <Async s={health} what="node information" ep={EP.health}>
              {(n) => (
                <dl className="info">
                  <Row
                    k="Node name"
                    v={pick(n, ['node_name', 'name'])}
                  />
                  <Row
                    k="Node ID"
                    v={pick(n, ['node_id', 'id', 'peer_id'])}
                  />
                  <Row
                    k="Hostname"
                    v={pick(n, ['hostname', 'host'])}
                  />
                  <Row
                    k="LAN IPv4"
                    v={pick(n, [
                      'lan_ip',
                      'lan_ipv4',
                      'ipv4',
                      'ip',
                      'ip_address',
                      'address',
                    ])}
                  />
                  <Row k="API status" v={apiStatus} />
                  <Row k="Uptime" v={uptime} />
                  <Row
                    k="Transfer port"
                    v={pick(n, ['transfer_port', 'tcp_port', 'port'])}
                  />
                  <Row
                    k="Discovery port"
                    v={pick(n, [
                      'discovery_port',
                      'udp_port',
                      'mdns_port',
                    ])}
                  />
                </dl>
              )}
            </Async>
          )}
        </Panel>
      </div>

      <Panel title="Transfer performance" meta="Samples every 3 seconds">
        <div className="ov-performance-stats">
          <div>
            <span>Current observed rate</span>
            <strong>{fmtBytes(latestRate)}/s</strong>
          </div>
          <div>
            <span>Peer traffic</span>
            <strong>{fmtBytes(peerBytes)}</strong>
          </div>
          <div>
            <span>Origin traffic</span>
            <strong>{fmtBytes(originBytes)}</strong>
          </div>
          <div>
            <span>Cache traffic</span>
            <strong>{fmtBytes(cacheBytes)}</strong>
          </div>
        </div>

        <div className="ov-chart">
          {traffic.length > 1 ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={traffic}>
                <defs>
                  <linearGradient id="peerlightTraffic" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="0%"
                      stopColor="var(--accent)"
                      stopOpacity={0.35}
                    />
                    <stop
                      offset="95%"
                      stopColor="var(--accent)"
                      stopOpacity={0.02}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--line)"
                />
                <XAxis
                  dataKey="time"
                  stroke="var(--mute)"
                  tick={{ fontSize: 11 }}
                  minTickGap={24}
                />
                <YAxis
                  stroke="var(--mute)"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(value: number) => `${fmtBytes(value)}/s`}
                  width={82}
                />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  formatter={(value: number) => [
                    `${fmtBytes(value)}/s`,
                    'Observed throughput',
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="bytesPerSecond"
                  name="Throughput"
                  stroke="var(--accent)"
                  fill="url(#peerlightTraffic)"
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="ov-chart-empty">
              <IconPulse />
              <strong>
                {trafficAvailable
                  ? 'Collecting traffic samples'
                  : 'Waiting for backend statistics'}
              </strong>
              <span>
                The graph needs at least two successful counter samples.
                Start a real transfer to see traffic increase.
              </span>
            </div>
          )}
        </div>
      </Panel>

      <div className="ov-grid">
        <Panel title="Cache and transfer summary">
          <div className="ov-summary">
            <div>
              <span>Estimated origin bytes saved</span>
              <strong>{fmtBytes(savedBytes)}</strong>
            </div>
            <div>
              <span>Total tracked transfers</span>
              <strong>{totalTransfers}</strong>
            </div>
            <div>
              <span>Completed</span>
              <strong className="good">{completedTransfers}</strong>
            </div>
            <div>
              <span>Failed</span>
              <strong className={failedTransfers ? 'bad' : ''}>
                {failedTransfers}
              </strong>
            </div>
            <div>
              <span>Total source traffic</span>
              <strong>{fmtBytes(totalTraffic)}</strong>
            </div>
          </div>
          <p className="ov-note">
            Values come from the backend's transfer counters. Saved bytes are
            estimates reported by the backend, not independently measured
            internet savings.
          </p>
        </Panel>

        <Panel title="Recent transfer activity" meta="Latest records">
          {!xfer.data?.length ? (
            <div className="ov-empty">
              <IconLog />
              <div>
                <strong>No transfers recorded yet</strong>
                Start a file transfer to populate this panel with real
                activity from the backend.
              </div>
            </div>
          ) : (
            <div className="tw">
              <table>
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Source</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTransfers.map((t, i) => (
                    <tr key={String(pick(t, ['id', 'transfer_id'], i))}>
                      <td className="clip">
                        {String(
                          pick(t, [
                            'name',
                            'filename',
                            'file',
                            'content_id',
                          ], 'Unknown file'),
                        )}
                      </td>
                      <td>
                        {String(
                          pick(t, ['peer', 'source', 'peer_id'], 'Not reported'),
                        )}
                      </td>
                      <td>
                        {String(pick(t, ['status', 'state'], 'Unknown'))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
