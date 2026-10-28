import { useEffect, useState } from 'react';
import { API_BASE } from './api';
import { useTheme } from './hooks';
import Overview from './pages/Overview';
import Peers from './pages/Peers';
import Transfers from './pages/Transfers';
import Analytics from './pages/Analytics';

const TABS = { overview: ['Overview', Overview], peers: ['Peers', Peers], transfers: ['Transfers', Transfers], analytics: ['Analytics', Analytics] } as const;
type Tab = keyof typeof TABS;
const fromHash = (): Tab => (location.hash.slice(1) in TABS ? (location.hash.slice(1) as Tab) : 'overview');

export default function App() {
  const [tab, setTab] = useState<Tab>(fromHash);
  const [theme, toggle] = useTheme();
  useEffect(() => { const f = () => setTab(fromHash()); addEventListener('hashchange', f); return () => removeEventListener('hashchange', f); }, []);
  const Page = TABS[tab][1];
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">Peerlight<small>P2P content delivery</small></div>
        <nav>{(Object.keys(TABS) as Tab[]).map((k) => <a key={k} href={`#${k}`} className={k === tab ? 'on' : ''}>{TABS[k][0]}</a>)}</nav>
        <div className="side-f"><code title="Backend base URL">{API_BASE}</code>
          <button className="btn" onClick={toggle} aria-label="Toggle theme">{theme === 'dark' ? 'Switch to light' : 'Switch to dark'}</button></div>
      </aside>
      <main className="main">{tab !== 'overview' && <h1>{TABS[tab][0]}</h1>}<Page /></main>
    </div>
  );
}
