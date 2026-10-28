# Peerlight — P2P CDN Frontend

React 18 + TypeScript + Vite dashboard for the P2P zero-configuration CDN. Charts: Recharts. Styling: plain CSS with theme variables (`src/styles.css`). Fonts: Bricolage Grotesque + Instrument Sans via Google Fonts (`index.html`; falls back to system fonts offline).

## Install and run
```bash
unzip p2p-cdn-frontend.zip -d p2p-cdn-frontend && cd p2p-cdn-frontend
npm install
cp .env.example .env      # then edit if needed
npm run dev               # http://localhost:5173 (also exposed on LAN)
```
Production: `npm run build && npm run preview` (serves `dist/` on port 4173), or host `dist/` with any static server.

## Connecting to the backend
- `VITE_API_BASE_URL` empty (default): the app calls `http://<hostname you opened the page on>:8000`. Opening `http://192.168.1.20:5173` from a phone makes it call `http://192.168.1.20:8000` automatically.
- Or set it explicitly, e.g. `VITE_API_BASE_URL=http://192.168.1.20:8000`, and restart `npm run dev` (env is read at start/build).
- Start FastAPI on all interfaces: `uvicorn main:app --host 0.0.0.0 --port 8000`.
- Enable CORS in FastAPI:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```
Allow ports 8000 and 5173/4173 in your firewall.

## Endpoints used (all configurable)
| Env var | Default | Used for |
|---|---|---|
| `VITE_EP_HEALTH` | `/api/health` | Backend status |
| `VITE_EP_NODE` | `/api/health` | This node's info |
| `VITE_EP_PEERS` | `/api/peers` | Peer list + topology |
| `VITE_EP_STATS` | `/api/stats` | Overview storage metrics |
| `VITE_EP_TRANSFERS` | `/api/transfers` | Transfer monitor |
| `VITE_EP_CACHE` | `/api/stats` | Cache analytics |
| `VITE_EP_BANDWIDTH` | `/api/bandwidth` | Bandwidth analytics |

Edit `src/api.ts` (`normPeer`, `normTransfer`) if your JSON field names differ. Responses may be a bare array, an object wrapping an array (`peers`, `transfers`, `items`, `data`), or an object keyed by id. Nothing is fabricated: if an endpoint returns 404 the UI says that view needs backend support; empty data shows an empty state.

Expected fields (aliases accepted): peers `id|peer_id|node_id`, `host|ip|address`, `port`, `status`, `latency_ms`, `last_seen`; transfers `id`, `file|filename|name`, `peer`, `status`, `progress` or `bytes_done/bytes_total`, `size`, `speed`; cache `hits`, `misses`, `size_bytes`, `capacity_bytes`, `items`; bandwidth `bytes_saved`, `bytes_from_peers`, `bytes_from_origin`, `series: [{t, peer, origin}]`.

## Theme
Dark/light toggle in the sidebar; saved in `localStorage` (`p2pcdn-theme`), defaulting to your OS preference.

## Troubleshooting
- **"Cannot reach backend"**: backend not running, wrong host, or not bound to `0.0.0.0`.
- **Works locally, fails from another device**: firewall, or backend bound to 127.0.0.1.
- **Browser console CORS error**: add the CORS middleware above.
- **"...aren't available from the backend"**: route returned 404; set the matching `VITE_EP_*` or add the route.
- **Mixed content**: don't serve the dashboard over HTTPS while the backend is HTTP.
- **Env changes ignored**: restart the dev server / rebuild.
