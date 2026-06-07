# Browser Shell and Search Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development
> to implement this plan task-by-task.

**Goal:** Deliver a React browser shell with schema/kind/value search that calls **GET `/api/v1/resolve`**, renders three-state UI (found / multiple / notFound), and passes the root node as a **seed** to a canvas placeholder — no `/expand` in this slice.

**Architecture:** New `codegraph_web/` Vite + React + TypeScript SPA; `useResolveSearch` hook drives a client-side phase machine; thin `api/` layer mirrors backend `ResolveResponse`; `AppShell` composes SearchBar + CanvasPlaceholder + StatusPanel. Dev uses Vite proxy to `codegraph-server`; production mounts `dist/` via FastAPI `StaticFiles`.

**Tech Stack:** React 18, Vite, TypeScript, Vitest, React Testing Library, CSS (no UI framework), FastAPI static mount

**Spec refs:** `openspec/changes/browser-shell-and-search/specs/browser-ui/spec.md`

**Design refs:** `openspec/changes/browser-shell-and-search/design.md`

---

## Task 1: Scaffold `codegraph_web/` (prerequisite)

- [ ] **Step 1:** From repo root, scaffold:

```bash
npm create vite@latest codegraph_web -- --template react-ts
cd codegraph_web && npm install
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

- [ ] **Step 2:** Add `vitest.config.ts` with `environment: 'jsdom'`, `setupFiles: './src/test/setup.ts'`
- [ ] **Step 3:** Create `src/test/setup.ts` — `import '@testing-library/jest-dom'`
- [ ] **Step 4:** Configure `vite.config.ts` proxy:

```typescript
server: {
  proxy: { '/api': 'http://127.0.0.1:8000' },
},
```

- [ ] **Step 5:** Add npm scripts: `"test": "vitest run"`, `"test:watch": "vitest"`
- [ ] **Step 6:** Run: `cd codegraph_web && npm run build && npm test` (empty pass)
- [ ] **Step 7:** Commit: `chore(web): scaffold codegraph_web with vite react-ts and vitest`

---

## Task 2: Types and API client (tasks §2.1, §3.4 foundation)

- [ ] **Step 1:** Create `src/types/graph.ts`:

```typescript
export type GraphNode = {
  type: string;
  id: number;
  title?: string | null;
  subtitle?: string | null;
};

export type ResolveStatus = 'notFound' | 'found' | 'multiple';

export type ResolveResponse = {
  status: ResolveStatus;
  roots: GraphNode[];
  candidates: GraphNode[];
};
```

- [ ] **Step 2:** Create `src/api/client.ts` — `apiGet(path: string): Promise<Response>` with base `''`
- [ ] **Step 3:** Create `src/api/resolve.test.ts` (RED):
  - builds URL `/api/v1/resolve?schema=S&kind=commandId&value=Cmd%201`
  - parses JSON into `ResolveResponse`
- [ ] **Step 4:** Create `src/api/resolve.ts` (GREEN):

```typescript
export async function resolveEntry(
  schema: string,
  kind: string,
  value: string,
): Promise<ResolveResponse> {
  const params = new URLSearchParams({ schema, kind, value });
  const res = await apiGet(`/api/v1/resolve?${params}`);
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}
```

- [ ] **Step 5:** Create `src/api/schemas.test.ts` — `listSchemas()` → `string[]`
- [ ] **Step 6:** Create `src/api/schemas.ts`:

```typescript
export async function listSchemas(): Promise<string[]> {
  const res = await apiGet('/api/v1/schemas');
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}
```

- [ ] **Step 7:** Run: `cd codegraph_web && npm test -- src/api`
- [ ] **Step 8:** Commit: `feat(web): add resolve and schemas API client`

---

## Task 3: Constants and entry kinds (tasks §3.1)

- [ ] **Step 1:** Create `src/constants/entryKinds.ts`:

```typescript
export const ENTRY_KINDS = [
  { value: 'commandId', label: 'Command ID' },
  { value: 'flowId', label: 'Flow ID' },
] as const;
export type EntryKind = (typeof ENTRY_KINDS)[number]['value'];
```

- [ ] **Step 2:** Create `src/constants/entryKinds.test.ts` — assert values `commandId` and `flowId` present
- [ ] **Step 3:** Run: `npm test -- src/constants`
- [ ] **Step 4:** Commit: `feat(web): add ENTRY_KINDS constants mirroring backend resolvers`

---

## Task 4: AppShell layout (tasks §1.1, §1.3, §6.8)

- [ ] **Step 1:** Create `src/components/AppShell.tsx` + `AppShell.css`:
  - regions: `header` (search), `main` (canvas), `footer` or `aside` (status)
  - CSS: `display: flex; flex-direction: column; min-height: 100vh`
  - narrow: `@media (max-width: 640px)` stack; `overflow-x: hidden`
- [ ] **Step 2:** Create `src/components/AppShell.test.tsx`:
  - renders `[data-testid="search-bar"]`, `[data-testid="canvas"]`, `[data-testid="status-panel"]`
  - narrow viewport test — all three regions in document
- [ ] **Step 3:** Wire into `App.tsx` with placeholder children
- [ ] **Step 4:** Run: `npm test -- AppShell`
- [ ] **Step 5:** Commit: `feat(web): add AppShell three-region layout with responsive CSS`

---

## Task 5: CanvasPlaceholder seed interface (tasks §1.2, §4.1)

- [ ] **Step 1:** Create `src/components/CanvasPlaceholder.tsx`:

```typescript
type Props = { seed: GraphNode | null };

export function CanvasPlaceholder({ seed }: Props) {
  if (!seed) return <div data-testid="canvas-empty">Select an entry to begin</div>;
  return (
    <div data-testid="canvas-seed">
      <span data-testid="seed-type">{seed.type}</span>
      <span data-testid="seed-id">{seed.id}</span>
      {seed.title && <span data-testid="seed-title">{seed.title}</span>}
      {seed.subtitle && <span data-testid="seed-subtitle">{seed.subtitle}</span>}
    </div>
  );
}
```

- [ ] **Step 2:** Create `src/components/CanvasPlaceholder.test.tsx`:
  - null seed → empty placeholder
  - seed → shows type, id, title, subtitle
- [ ] **Step 3:** Run: `npm test -- CanvasPlaceholder`
- [ ] **Step 4:** Commit: `feat(web): add CanvasPlaceholder seed display`

---

## Task 6: SchemaSelect (tasks §2.1, §2.2)

- [ ] **Step 1:** Create `src/components/SchemaSelect.tsx` — props: `schemas: string[]`, `value`, `onChange`, `disabled?`
- [ ] **Step 2:** In `App.tsx` or parent, `useEffect` → `listSchemas()` on mount; handle load error gracefully
- [ ] **Step 3:** Create `src/components/SchemaSelect.test.tsx` — renders options, fires onChange
- [ ] **Step 4:** Run: `npm test -- SchemaSelect`
- [ ] **Step 5:** Commit: `feat(web): add SchemaSelect from /api/v1/schemas`

---

## Task 7: SearchBar controls (tasks §3.1–§3.3)

- [ ] **Step 1:** Create `KindSelect.tsx` — maps `ENTRY_KINDS` to `<select>`
- [ ] **Step 2:** Create `SearchBar.tsx` — composes SchemaSelect + KindSelect + value `<input>` + submit button
- [ ] **Step 3:** Validation rules:
  - no schema → submit disabled + `data-validation="schema-required"`
  - empty value → submit disabled or onSubmit shows inline hint, **no API call**
  - loading → submit disabled (`aria-busy`)
- [ ] **Step 4:** Create `SearchBar.test.tsx`:
  - empty value submit → `resolveEntry` not called (mock)
  - no schema → submit disabled
- [ ] **Step 5:** Run: `npm test -- SearchBar`
- [ ] **Step 6:** Commit: `feat(web): add SearchBar with kind/value validation`

---

## Task 8: useResolveSearch hook (tasks §3.4, §5.1)

- [ ] **Step 1:** Create `src/hooks/useResolveSearch.test.ts` (RED):
  - submit → phase `loading` then `found` with seed
  - double submit while loading → `resolveEntry` called once
  - `notFound` → phase `notFound`, seed null
  - `multiple` → phase `multiple`, candidates populated
  - fetch error → phase `error`
- [ ] **Step 2:** Create `src/hooks/useResolveSearch.ts` (GREEN):

```typescript
type Phase = 'idle' | 'loading' | 'found' | 'multiple' | 'notFound' | 'error';

export function useResolveSearch() {
  const [phase, setPhase] = useState<Phase>('idle');
  const [seed, setSeed] = useState<GraphNode | null>(null);
  const [candidates, setCandidates] = useState<GraphNode[]>([]);
  const [lastQuery, setLastQuery] = useState<Query | null>(null);
  const inFlight = useRef(false);

  async function submit(query: Query) { /* guard inFlight, call resolveEntry, map status */ }
  function selectCandidate(node: GraphNode) { setSeed(node); setPhase('found'); }
  async function retry() { if (lastQuery) await submit(lastQuery); }

  return { phase, seed, candidates, submit, selectCandidate, retry, ... };
}
```

- [ ] **Step 3:** Run: `npm test -- useResolveSearch`
- [ ] **Step 4:** Commit: `feat(web): add useResolveSearch state machine`

---

## Task 9: Status components — three states + loading/error (tasks §4, §5)

- [ ] **Step 1:** Create `EmptyState.tsx` — neutral styling (not error red); `data-testid="empty-state"`
- [ ] **Step 2:** Create `ErrorState.tsx` — error styling + Retry button; `data-testid="error-state"`
- [ ] **Step 3:** Create `CandidateList.tsx` — list buttons with title/subtitle per candidate
- [ ] **Step 4:** Create `StatusPanel.tsx` — switch on `phase`:
  - `loading` → spinner / "Searching…"
  - `notFound` → EmptyState
  - `multiple` → CandidateList
  - `error` → ErrorState
  - else → null or idle
- [ ] **Step 5:** Create `StatusPanel.test.tsx` for each phase
- [ ] **Step 6:** Run: `npm test -- StatusPanel EmptyState ErrorState CandidateList`
- [ ] **Step 7:** Commit: `feat(web): add StatusPanel with three-state and error UI`

---

## Task 10: App integration (tasks §4.1–§4.4, §6.1–§6.7)

- [ ] **Step 1:** Wire `App.tsx`:
  - `useResolveSearch()` + SearchBar `onSubmit={submit}`
  - `CanvasPlaceholder seed={seed}`
  - `StatusPanel` with phase/candidates/retry/onSelect
- [ ] **Step 2:** Create `src/App.test.tsx` integration tests (mock `api/resolve`):
  - **6.1** found → seed in canvas (`data-testid="canvas-seed"`)
  - **6.2** multiple → candidates with title/subtitle
  - **6.3** pick candidate → seed updates
  - **6.4** notFound → empty-state, no error-state
  - **6.5** API 500 → error-state + retry works on second mock
  - **6.6** no schema / empty value → resolve not called
  - **6.7** loading double-click → one call
- [ ] **Step 3:** Run: `cd codegraph_web && npm test`
- [ ] **Step 4:** Commit: `feat(web): integrate shell search resolve flow`

---

## Task 11: Narrow-screen test (tasks §1.3, §6.8)

- [ ] **Step 1:** Add `AppShell.test.tsx` or `App.test.tsx` case with `window.matchMedia` / viewport width 375
- [ ] **Step 2:** Assert no `document.documentElement.scrollWidth > clientWidth` (or all three testids visible)
- [ ] **Step 3:** Run: `npm test`
- [ ] **Step 4:** Commit: `test(web): narrow-screen layout accessibility`

---

## Task 12: FastAPI static mount (design §5 — production)

- [ ] **Step 1:** Build frontend: `cd codegraph_web && npm run build`
- [ ] **Step 2:** Update `codegraph_server/app.py`:

```python
from fastapi.staticfiles import StaticFiles

_DIST = _REPO_ROOT / "codegraph_web" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
```

  - Mount **after** `app.include_router(router)` so `/api/v1/*` takes precedence
  - Or mount at `/app` if root conflict — prefer root per design

- [ ] **Step 3:** Add note to `codegraph_web/README.md`:

```markdown
## Dev
npm run dev          # :5173, proxies /api → :8000
python codegraph_server/app.py   # :8000

## Prod
npm run build && python codegraph_server/app.py   # serves dist at /
```

- [ ] **Step 4:** Manual smoke: build + start server, open `/`, submit search against live MySQL
- [ ] **Step 5:** Commit: `feat(server): mount codegraph_web dist for production SPA`

---

## Task 13: OpenSpec apply checklist sync

- [ ] **Step 1:** Run full test suite:

```bash
cd codegraph_web && npm test
pytest codegraph_core/graph/ codegraph_server/test_*_route.py -q
```

- [ ] **Step 2:** Check off all items in `openspec/changes/browser-shell-and-search/tasks.md`
- [ ] **Step 3:** Commit: `docs(openspec): mark browser-shell-and-search tasks complete`

---

## Verification commands (for `/opsx:verify`)

```bash
cd codegraph_web && npm test
cd .. && pytest codegraph_server/test_resolve_route.py -q
openspec validate --all --json
```

Manual:

1. `docker compose up -d && python codegraph_server/app.py`
2. `cd codegraph_web && npm run dev`
3. Select schema → commandId + known value → seed appears
4. Unknown value → empty state (not red error)
5. Resize to mobile width → three regions usable

---

## Commit sequence summary

1. `chore(web): scaffold codegraph_web with vite react-ts and vitest`
2. `feat(web): add resolve and schemas API client`
3. `feat(web): add ENTRY_KINDS constants mirroring backend resolvers`
4. `feat(web): add AppShell three-region layout with responsive CSS`
5. `feat(web): add CanvasPlaceholder seed display`
6. `feat(web): add SchemaSelect from /api/v1/schemas`
7. `feat(web): add SearchBar with kind/value validation`
8. `feat(web): add useResolveSearch state machine`
9. `feat(web): add StatusPanel with three-state and error UI`
10. `feat(web): integrate shell search resolve flow`
11. `test(web): narrow-screen layout accessibility`
12. `feat(server): mount codegraph_web dist for production SPA`
13. `docs(openspec): mark browser-shell-and-search tasks complete`
