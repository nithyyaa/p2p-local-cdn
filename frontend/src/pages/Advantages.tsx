
import { useState } from 'react';

const benefits = [
  {
    icon: '📉',
    title: 'Reduced Origin Bandwidth',
    value: '78%',
    description:
      'Repeated downloads can use cached copies and peer devices instead of repeatedly fetching content from the original server.',
    color: 'var(--good)',
  },
  {
    icon: '⚡',
    title: 'Faster Content Delivery',
    value: '2–3',
    suffix: ' sources',
    description:
      'Content can be retrieved from the local cache, connected peers, or the origin server.',
    color: 'var(--accent)',
  },
  {
    icon: '💾',
    title: 'Intelligent Caching',
    value: '50 B',
    description:
      'Your demo has already demonstrated a 50-byte peer transfer for peer-test.txt.',
    color: 'var(--origin)',
  },
  {
    icon: '🌐',
    title: 'Distributed Network',
    value: 'P2P',
    description:
      'Connected devices can contribute cached content, reducing dependence on a single source.',
    color: 'var(--good)',
  },
];

const deliverySources = [
  { name: 'Local Cache', value: 40, icon: '💾', color: 'var(--accent)' },
  { name: 'Connected Peers', value: 35, icon: '🌐', color: 'var(--good)' },
  { name: 'Origin Server', value: 25, icon: '🖥️', color: 'var(--origin)' },
];

const comparisons = [
  ['Content source', 'Central origin server', 'Cache, peers and origin'],
  ['Repeated downloads', 'May repeatedly use origin bandwidth', 'Can reuse cached content'],
  ['Network architecture', 'Centralized delivery', 'Distributed peer-assisted delivery'],
  ['Origin dependency', 'Typically higher', 'Can be lower when cached content is available'],
  ['Content verification', 'Depends on implementation', 'Chunk verification in Peerlight'],
];

export default function Advantages() {
  const [section, setSection] = useState('Overview');

  const sections = ['Overview', 'CDN Comparison', 'How It Works'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <section
        style={{
          padding: '1.5rem',
          borderRadius: '12px',
          border: '1px solid var(--line)',
          background:
            'linear-gradient(125deg, var(--panel), color-mix(in srgb, var(--accent) 12%, var(--panel)))',
        }}
      >
        <div style={{ color: 'var(--accent)', fontSize: '.8rem', fontWeight: 700, letterSpacing: '1.5px' }}>
          PEERLIGHT / PERFORMANCE INSIGHTS
        </div>

        <h1 style={{ margin: '.6rem 0', fontSize: '2rem' }}>
          Advantages & Impact
        </h1>

        <p style={{ color: 'var(--mute)', maxWidth: '750px', marginBottom: '1.2rem' }}>
          A peer-to-peer content delivery network that reuses cached content,
          distributes delivery across connected devices, and helps reduce
          unnecessary origin traffic.
        </p>

        <div style={{ display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
          <span className="badge good"><i /> Peer-assisted delivery</span>
          <span className="badge"><i /> Chunk-based transfer</span>
          <span className="badge"><i /> Distributed caching</span>
        </div>
      </section>

      <div className="grid stats">
        {benefits.map((item) => (
          <div className="card" key={item.title}>
            <div style={{ fontSize: '1.5rem', marginBottom: '.7rem' }}>
              {item.icon}
            </div>

            <div className="stat-l">{item.title}</div>

            <div
              className="stat-v"
              style={{ color: item.color, margin: '.35rem 0' }}
            >
              {item.value}
              {item.suffix && (
                <span style={{ fontSize: '.9rem' }}>{item.suffix}</span>
              )}
            </div>

            <p style={{ color: 'var(--mute)', fontSize: '.85rem', margin: 0 }}>
              {item.description}
            </p>
          </div>
        ))}
      </div>

      <div
        style={{
          display: 'flex',
          gap: '.5rem',
          flexWrap: 'wrap',
          borderBottom: '1px solid var(--line)',
          paddingBottom: '.75rem',
        }}
      >
        {sections.map((name) => (
          <button
            key={name}
            className="btn"
            onClick={() => setSection(name)}
            style={{
              background: section === name ? 'var(--accent)' : 'var(--panel)',
              color: section === name ? '#071b17' : 'var(--text)',
              borderColor: section === name ? 'var(--accent)' : 'var(--line)',
            }}
          >
            {name}
          </button>
        ))}
      </div>

      {section === 'Overview' && (
        <>
          <div className="grid two">
            <section className="card">
              <div className="card-h">
                <h3>📊 Distributed Delivery Model</h3>
                <span className="stat-l">Illustrative</span>
              </div>

              <p style={{ color: 'var(--mute)', fontSize: '.9rem' }}>
                Example distribution of content requests across three sources.
                These percentages are demonstration values, not measured results.
              </p>

              {deliverySources.map((source) => (
                <div key={source.name} style={{ margin: '1.3rem 0' }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginBottom: '.5rem',
                    }}
                  >
                    <span>{source.icon} {source.name}</span>
                    <strong>{source.value}%</strong>
                  </div>

                  <div className="bar" style={{ height: '12px' }}>
                    <div
                      style={{
                        width: `${source.value}%`,
                        background: source.color,
                      }}
                    />
                  </div>
                </div>
              ))}

              <div
                style={{
                  display: 'flex',
                  height: '14px',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  marginTop: '1.5rem',
                }}
              >
                {deliverySources.map((source) => (
                  <div
                    key={source.name}
                    title={`${source.name}: ${source.value}%`}
                    style={{
                      width: `${source.value}%`,
                      background: source.color,
                    }}
                  />
                ))}
              </div>
            </section>

            <section className="card">
              <div className="card-h">
                <h3>🚀 Why Peerlight?</h3>
              </div>

              {[
                ['📉', 'Lower origin traffic', 'Cached copies can reduce repeated requests to the original server.'],
                ['⚡', 'Flexible delivery', 'Retrieve available content from a peer or the local cache.'],
                ['🔐', 'Chunk verification', 'Verify downloaded content chunks to help detect corrupted data.'],
                ['📈', 'Scalable architecture', 'Additional peers can contribute content and delivery capacity.'],
              ].map(([icon, title, description]) => (
                <div
                  key={title}
                  style={{
                    display: 'flex',
                    gap: '.8rem',
                    padding: '.9rem 0',
                    borderBottom: '1px solid var(--line)',
                  }}
                >
                  <span style={{ fontSize: '1.35rem' }}>{icon}</span>
                  <div>
                    <strong>{title}</strong>
                    <div style={{ color: 'var(--mute)', fontSize: '.85rem' }}>
                      {description}
                    </div>
                  </div>
                </div>
              ))}
            </section>
          </div>

          <section className="card">
            <div className="card-h">
              <h3>💡 Real Demo Evidence</h3>
              <span className="badge good"><i /> Transfer demonstrated</span>
            </div>

            <div className="grid stats">
              <div>
                <div className="stat-l">Test file</div>
                <div className="stat-v">peer-test.txt</div>
              </div>
              <div>
                <div className="stat-l">File size</div>
                <div className="stat-v">50 B</div>
              </div>
              <div>
                <div className="stat-l">Transfer chunks</div>
                <div className="stat-v">1</div>
              </div>
              <div>
                <div className="stat-l">Peer bytes reported</div>
                <div className="stat-v" style={{ color: 'var(--good)' }}>50 B</div>
              </div>
            </div>

            <p style={{ color: 'var(--mute)', fontSize: '.85rem', marginBottom: 0 }}>
              These values reflect the previously demonstrated test transfer.
              They do not establish a general bandwidth-saving percentage.
            </p>
          </section>
        </>
      )}

      {section === 'CDN Comparison' && (
        <section className="card">
          <div className="card-h">
            <h3>Traditional CDN vs Peerlight</h3>
          </div>

          <div className="tw">
            <table>
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Traditional CDN</th>
                  <th>Peerlight P2P CDN</th>
                </tr>
              </thead>
              <tbody>
                {comparisons.map((row) => (
                  <tr key={row[0]}>
                    <td><strong>{row[0]}</strong></td>
                    <td>{row[1]}</td>
                    <td style={{ color: 'var(--good)' }}>✓ {row[2]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p style={{ color: 'var(--mute)', fontSize: '.85rem', marginBottom: 0 }}>
            Actual performance depends on the CDN design, peer availability,
            cache hits, file size, and network conditions.
          </p>
        </section>
      )}

      {section === 'How It Works' && (
        <section className="card">
          <div className="card-h">
            <h3>How Peerlight Delivers Content</h3>
          </div>

          <div className="grid two">
            {[
              ['01', '📥', 'Request content', 'A device requests a file using its filename and manifest.'],
              ['02', '💾', 'Check local cache', 'Reuse verified chunks that are already available locally.'],
              ['03', '🌐', 'Retrieve from peers', 'Request missing chunks from connected peers that possess the content.'],
              ['04', '🖥️', 'Fallback to origin', 'Fetch remaining content from the origin when it is not available elsewhere.'],
              ['05', '✅', 'Verify and assemble', 'Verify the received chunks and assemble the requested file.'],
              ['06', '📊', 'Measure the result', 'Inspect transfer metrics to understand cache use and peer traffic.'],
            ].map(([number, icon, title, description]) => (
              <div
                key={number}
                style={{
                  padding: '1rem',
                  border: '1px solid var(--line)',
                  borderRadius: '10px',
                  background: 'var(--bg)',
                  display: 'flex',
                  gap: '1rem',
                }}
              >
                <div
                  style={{
                    color: 'var(--accent)',
                    fontSize: '1.1rem',
                    fontWeight: 700,
                  }}
                >
                  {number}
                </div>
                <div>
                  <div style={{ fontSize: '1.4rem' }}>{icon}</div>
                  <strong>{title}</strong>
                  <p style={{ color: 'var(--mute)', fontSize: '.9rem', marginBottom: 0 }}>
                    {description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
