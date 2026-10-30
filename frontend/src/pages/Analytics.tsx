import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, EP, fmtBytes, pick } from '../api';
import { usePoll } from '../hooks';
import { Async, Card, Empty, Stat } from '../components/ui';

const tip = {
  background: 'var(--panel)',
  border: '1px solid var(--line)',
};

export default function Analytics() {
  const stats = usePoll(() => api(EP.stats), 3000);
  const transfers = usePoll(() => api(EP.transfers), 3000);

  return (
    <div style={{ display: 'grid', gap: '1rem' }}>
      <Card title="Cache & Storage">
        <Async s={stats} what="cache statistics" ep={EP.stats}>
          {(data) => {
            const cachedBytes = pick(data, ['cached_bytes'], 0);
            const cachedChunks = pick(data, ['cached_chunks'], 0);
            const metrics = pick(data, ['transfer_metrics'], {});

            const sources = [
              {
                name: 'Peer traffic',
                value: pick(metrics, ['peer_bytes'], 0),
              },
              {
                name: 'Origin traffic',
                value: pick(metrics, ['origin_bytes'], 0),
              },
              {
                name: 'Cache traffic',
                value: pick(metrics, ['cache_bytes'], 0),
              },
            ].filter((item) => item.value > 0);

            return (
              <>
                <div className="grid stats">
                  <Stat
                    label="Cached storage"
                    value={fmtBytes(cachedBytes)}
                    hint="Current local chunk storage"
                  />
                  <Stat
                    label="Cached chunks"
                    value={cachedChunks}
                    hint="Chunks stored on this node"
                  />
                  <Stat
                    label="Origin traffic saved"
                    value={fmtBytes(
                      pick(metrics, ['estimated_origin_bytes_saved'], 0),
                    )}
                    hint="Based on tracked peer and cache bytes"
                  />
                </div>

                <div className="chart">
                  <h3>Traffic source breakdown</h3>
                  {sources.length ? (
                    <ResponsiveContainer width="100%" height={260}>
                      <PieChart>
                        <Pie
                          data={sources}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={90}
                          label={({ name }) => name}
                        >
                          {sources.map((source, index) => (
                            <Cell
                              key={source.name}
                              fill={
                                [
                                  'var(--accent)',
                                  'var(--warn)',
                                  '#818cf8',
                                ][index % 3]
                              }
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: number) => fmtBytes(value)}
                          contentStyle={tip}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <Empty
                      title="No transfer traffic recorded"
                      hint="This chart will populate when actual transfers are tracked."
                    />
                  )}
                </div>
              </>
            );
          }}
        </Async>
      </Card>

      <Card title="Transfer Analytics">
        <Async s={stats} what="transfer statistics" ep={EP.stats}>
          {(data) => {
            const metrics = pick(data, ['transfer_metrics'], {});

            const counts = [
              {
                name: 'Completed',
                count: pick(metrics, ['completed_transfers'], 0),
              },
              {
                name: 'Active',
                count: pick(metrics, ['active_transfers'], 0),
              },
              {
                name: 'Failed',
                count: pick(metrics, ['failed_transfers'], 0),
              },
            ];

            return (
              <>
                <div className="grid stats">
                  <Stat
                    label="Total transfers"
                    value={pick(metrics, ['total_transfers'], 0)}
                  />
                  <Stat
                    label="Completed"
                    value={pick(metrics, ['completed_transfers'], 0)}
                  />
                  <Stat
                    label="Failed"
                    value={pick(metrics, ['failed_transfers'], 0)}
                  />
                </div>

                <div className="chart">
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={counts}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="var(--line)"
                      />
                      <XAxis dataKey="name" stroke="var(--mute)" />
                      <YAxis
                        stroke="var(--mute)"
                        allowDecimals={false}
                      />
                      <Tooltip contentStyle={tip} />
                      <Bar
                        dataKey="count"
                        name="Transfers"
                        fill="var(--accent)"
                        radius={[5, 5, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </>
            );
          }}
        </Async>
      </Card>

      <Card title="Recent Transfer Records">
        <Async s={transfers} what="transfer records" ep={EP.transfers}>
          {(data) => {
            const records = pick(data, ['transfers', 'items', 'data'], {});

            const rows = Array.isArray(records)
              ? records
              : Object.entries(records).map(([id, value]) => ({
                  id,
                  ...(value as object),
                }));

            return rows.length ? (
              <div className="tw">
                <table>
                  <thead>
                    <tr>
                      <th>File</th>
                      <th>Source</th>
                      <th>Status</th>
                      <th>Bytes transferred</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row: any, index: number) => (
                      <tr key={row.id ?? index}>
                        <td className="clip">
                          {row.name ?? row.file ?? 'Unknown file'}
                        </td>
                        <td>{row.peer ?? 'Not reported'}</td>
                        <td>{row.status ?? 'Unknown'}</td>
                        <td>{fmtBytes(row.bytes_done ?? row.bytes)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty
                title="No transfers recorded"
                hint="Real transfer records will appear here after files are downloaded."
              />
            );
          }}
        </Async>
      </Card>
    </div>
  );
}