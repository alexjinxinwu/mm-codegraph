# codegraph_web

Browser shell for codegraph — search by commandId / flowId via `/api/v1/resolve`.

## Dev

```bash
# Terminal 1 — API (requires MySQL)
docker compose up -d
python codegraph_server/app.py   # :8000

# Terminal 2 — frontend (proxies /api → :8000)
cd codegraph_web
npm install
npm run dev                      # :5173
```

## Prod

```bash
cd codegraph_web && npm run build
python codegraph_server/app.py   # serves dist/ at /
```

## Test

```bash
npm test
```
