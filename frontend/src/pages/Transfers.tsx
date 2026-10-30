import { useState } from 'react';
import { api, API_BASE, EP, fmtBytes, normTransfer, toList } from '../api';
import { usePoll } from '../hooks';
import { Async, Badge, Bar, Card, Empty } from '../components/ui';

export default function Transfers() {
  const s = usePoll(
    async () =>
      toList(await api(EP.transfers), ['transfers', 'items', 'data']).map(
        normTransfer,
      ),
    3000,
  );

  const [fileName, setFileName] = useState('');
  const [manifest, setManifest] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function prepareFile() {
    const name = fileName.trim();

    if (!name) {
      setError('Enter the exact filename available in the origin folder.');
      return;
    }

    setBusy(true);
    setError('');
    setMessage('');

    try {
      const result = await fetch(`${API_BASE}/api/files/manifest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(import.meta.env.VITE_API_KEY
            ? { 'X-API-Key': import.meta.env.VITE_API_KEY }
            : {}),
        },
        body: JSON.stringify({ file_name: name }),
      });

      const data = await result.json();

      if (!result.ok) {
        throw new Error(data.detail || `HTTP ${result.status}`);
      }

      setManifest(data.manifest);
      setMessage(
        `Manifest ready: ${data.manifest.file_name} (${fmtBytes(data.manifest.file_size)}).`,
      );
    } catch (e: any) {
      setError(e.message || 'Could not prepare the file.');
      setManifest(null);
    } finally {
      setBusy(false);
    }
  }

  async function downloadFile() {
    if (!manifest) return;

    setBusy(true);
    setError('');
    setMessage('Downloading and assembling file. Please wait…');

    try {
      const response = await fetch(`${API_BASE}/api/files/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(import.meta.env.VITE_API_KEY
            ? { 'X-API-Key': import.meta.env.VITE_API_KEY }
            : {}),
        },
        body: JSON.stringify({ manifest }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');

      anchor.href = url;
      anchor.download = manifest.file_name || fileName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);

      setMessage(
        `Download completed: ${manifest.file_name || fileName} (${fmtBytes(blob.size)}).`,
      );
      setManifest(null);
      setFileName('');
      
    } catch (e: any) {
      setError(e.message || 'Download failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: 'grid', gap: '1rem' }}>
      <Card title="Download content">
        <p style={{ color: 'var(--muted, #94a3b8)', marginTop: 0 }}>
          Enter a filename available in this node's origin directory. Peerlight
          prepares its chunk manifest, retrieves content through its existing
          cache/peer/origin logic, and verifies chunks.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void prepareFile();
          }}
          style={{
            display: 'flex',
            gap: '.75rem',
            flexWrap: 'wrap',
            alignItems: 'center',
          }}
        >
          <input
            aria-label="Origin filename"
            placeholder="Example: demo-video.mp4"
            value={fileName}
            onChange={(e) => {
              setFileName(e.target.value);
              setManifest(null);
            }}
            disabled={busy}
            style={{
              flex: '1 1 260px',
              minWidth: 0,
              padding: '.8rem 1rem',
              borderRadius: '10px',
              border: '1px solid var(--border, #334155)',
              background: 'var(--panel, #111827)',
              color: 'inherit',
            }}
          />

          <button type="submit" disabled={busy || !fileName.trim()}>
            {busy ? 'Working…' : 'Prepare file'}
          </button>

          <button
            type="button"
            onClick={() => void downloadFile()}
            disabled={busy || !manifest}
          >
            Download file
          </button>
        </form>

        {manifest && (
          <p style={{ marginBottom: 0 }}>
            Ready: <strong>{manifest.file_name}</strong> ·{' '}
            {manifest.chunks?.length ?? 0} chunks ·{' '}
            {fmtBytes(manifest.file_size)}
          </p>
        )}

        {message && (
          <p role="status" style={{ color: '#2dd4bf' }}>
            {message}
          </p>
        )}

        {error && (
          <p role="alert" style={{ color: '#fb7185' }}>
            {error}
          </p>
        )}
      </Card>

      <Card title="Transfer history">
        <Async s={s} what="transfers" ep={EP.transfers}>
          {(rows) =>
            !rows.length ? (
              <Empty
                title="No transfers yet"
                hint="Completed and active transfers will appear here when reported by the backend."
              />
            ) : (
              <div className="tw">
                <table>
                  <thead>
                    <tr>
                      <th>Content</th>
                      <th>Peer / Source</th>
                      <th>Status</th>
                      <th>Progress</th>
                      <th>Size</th>
                      <th>Speed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((t) => (
                      <tr key={t.id}>
                        <td className="clip">{t.name}</td>
                        <td>{t.peer}</td>
                        <td>
                          <Badge status={t.status} />
                        </td>
                        <td className="w">
                          {t.progress === undefined ? (
                            '—'
                          ) : (
                            <Bar pct={t.progress} />
                          )}
                        </td>
                        <td>{fmtBytes(t.bytes)}</td>
                        <td>
                          {typeof t.speed === 'number'
                            ? `${fmtBytes(t.speed)}/s`
                            : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
        </Async>
      </Card>
    </div>
  );
}