import { api, EP, fmtBytes, normTransfer, toList } from '../api';
import { usePoll } from '../hooks';
import { Async, Badge, Bar, Card, Empty } from '../components/ui';

export default function Transfers() {
  const s = usePoll(async () => toList(await api(EP.transfers), ['transfers', 'items', 'data']).map(normTransfer), 3000);
  return (
    <Card title="Transfers">
      <Async s={s} what="transfers" ep={EP.transfers}>{(rows) => !rows.length
        ? <Empty title="No transfers yet" hint="Transfers appear when this node serves or fetches content from a peer." />
        : <div className="tw"><table><thead><tr><th>Content</th><th>Peer</th><th>Status</th><th>Progress</th><th>Size</th><th>Speed</th></tr></thead>
          <tbody>{rows.map((t) => <tr key={t.id}><td className="clip">{t.name}</td><td>{t.peer}</td><td><Badge status={t.status} /></td>
            <td className="w">{t.progress === undefined ? '—' : <Bar pct={t.progress} />}</td>
            <td>{fmtBytes(t.bytes)}</td><td>{typeof t.speed === 'number' ? `${fmtBytes(t.speed)}/s` : '—'}</td></tr>)}</tbody></table></div>}
      </Async>
    </Card>
  );
}
