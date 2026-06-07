# Graph Canvas Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development
> to implement this plan task-by-task.

**Goal:** Replace `CanvasPlaceholder` with an incremental **React Flow** canvas that renders seed nodes, expands on click via **POST `/api/v1/expand`**, dedupes merges, stable incremental layout, and per-node loading/error/retry.

**Architecture:** Pure `graph/` modules (`keys`, `graphStore`, `layout`) + `useGraphCanvas` hook + `GraphCanvas`/`CodegraphNode` UI. Lift `schema` to `App` for expand calls. No backend changes.

**Tech Stack:** React 19, Vite, TypeScript, `@xyflow/react`, `@dagrejs/dagre`, Vitest, RTL

**Spec refs:** `openspec/changes/graph-canvas/specs/graph-browser/spec.md`

**Design refs:** `openspec/changes/graph-canvas/design.md`

---

## Task 1: Dependencies and expand API client

- [ ] **Step 1:** Install graph libs:

```bash
cd codegraph_web
npm install @xyflow/react @dagrejs/dagre
```

- [ ] **Step 2:** Extend `src/types/graph.ts`:

```typescript
export type NodeRef = { type: string; id: number };

export type GraphEdge = {
  ruleId: string;
  from: NodeRef;
  to: NodeRef;
  label: string;
};

export type ExpandResponse = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};
```

- [ ] **Step 3:** Create `src/api/expand.test.ts` (RED) — POST body `{ schema, node: { type, id } }`, parse response
- [ ] **Step 4:** Create `src/api/expand.ts` (GREEN):

```typescript
export async function expandNode(
  schema: string,
  node: NodeRef,
): Promise<ExpandResponse> {
  const res = await fetch('/api/v1/expand', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schema, node }),
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}
```

- [ ] **Step 5:** Run: `npm test -- src/api/expand`
- [ ] **Step 6:** Commit: `feat(web): add expand API client and graph edge types`

---

## Task 2: Graph keys and store (tasks §1)

- [ ] **Step 1:** Create `src/graph/keys.ts`:

```typescript
export function nodeKey(n: NodeRef): string {
  return `${n.type}:${n.id}`;
}

export function edgeKey(e: GraphEdge): string {
  return `${e.ruleId}:${e.from.type}:${e.from.id}:${e.to.type}:${e.to.id}`;
}
```

- [ ] **Step 2:** Create `src/graph/keys.test.ts` — stable keys for sample node/edge
- [ ] **Step 3:** Create `src/graph/graphStore.ts`:

```typescript
export type GraphNodeState = GraphNode & { expanded?: boolean };

export type GraphState = {
  nodes: Map<string, GraphNodeState>;
  edges: Map<string, GraphEdge>;
  positions: Map<string, { x: number; y: number }>;
  expandPhase: Map<string, 'idle' | 'loading' | 'error'>;
};

export function createFromSeed(seed: GraphNode): GraphState;
export function mergeExpandResult(
  state: GraphState,
  sourceKey: string,
  response: ExpandResponse,
): { state: GraphState; addedNodeKeys: string[]; addedEdgeKeys: string[] };
```

- [ ] **Step 4:** Create `src/graph/graphStore.test.ts`:
  - `createFromSeed` → single node, no edges, position at origin
  - merge adds new nodes/edges
  - **6.3** duplicate node skipped
  - **6.4** duplicate edge skipped
  - source marked `expanded: true` after merge helper `markExpanded(state, key)`

- [ ] **Step 5:** Run: `npm test -- src/graph/keys src/graph/graphStore`
- [ ] **Step 6:** Commit: `feat(web): add graph store with dedupe merge`

---

## Task 3: Incremental layout (tasks §4)

- [ ] **Step 1:** Create `src/graph/layout.ts`:

```typescript
export function layoutNewNodes(
  state: GraphState,
  anchorKey: string,
  newNodeKeys: string[],
): Map<string, { x: number; y: number }>;
```

  - Preserve all existing `positions`
  - Run dagre on subgraph `{ anchor } ∪ newNodeKeys` + incident new edges
  - Translate subgraph so anchor keeps prior coordinates
  - Return updated positions map (only new keys changed from undefined)

- [ ] **Step 2:** Create `src/graph/layout.test.ts`:
  - anchor position unchanged after layout
  - new node placed within radius of anchor (e.g. distance < 400)
  - **6.9** existing node coords unchanged (delta 0)

- [ ] **Step 3:** Run: `npm test -- src/graph/layout`
- [ ] **Step 4:** Commit: `feat(web): add incremental dagre layout for new nodes`

---

## Task 4: Node type colors (tasks §2.2, §6.5)

- [ ] **Step 1:** Create `src/constants/nodeTypeColors.ts` — map 14 graph-core types → CSS border color
- [ ] **Step 2:** Create `src/constants/nodeTypeColors.test.ts` — `service_entry` ≠ `flow` colors
- [ ] **Step 3:** Commit: `feat(web): add node type color palette`

---

## Task 5: CodegraphNode component (tasks §2.1, §2.4, §5)

- [ ] **Step 1:** Create `src/components/CodegraphNode.tsx` (React Flow `NodeProps`):

```typescript
// data: { title, subtitle, nodeType, expanded, phase, onRetry }
// Render title/subtitle, type badge, node-type--{type} class
// phase loading → data-testid="node-loading"
// phase error → data-testid="node-error" + Retry button calling data.onRetry
// expanded → data-testid="node-expanded"
```

- [ ] **Step 2:** Create `src/components/CodegraphNode.test.tsx` — render with mock data for each phase
- [ ] **Step 3:** Create `src/components/graphCanvas.css` — node borders, loading overlay, error style
- [ ] **Step 4:** Run: `npm test -- CodegraphNode`
- [ ] **Step 5:** Commit: `feat(web): add CodegraphNode with expand states`

---

## Task 6: useGraphCanvas hook (tasks §3, §5)

- [ ] **Step 1:** Create `src/graph/useGraphCanvas.test.ts` (RED, mock `expandNode`):
  - seed set → one RF node
  - click triggers expand with schema + node
  - loading blocks second click on same node (**6.8**)
  - error sets phase error; retry re-calls expand (**6.7**)
  - expanded node click → no second expand
  - node A loading does not block expand on node B (**6.6**, **5.4**)

- [ ] **Step 2:** Create `src/graph/useGraphCanvas.ts` (GREEN):
  - `useEffect` reset on `seed` change
  - `onNodeClick` → guard expanded/loading → expand → merge → layout → set RF nodes/edges
  - `onRetry(nodeKey)` for error recovery
  - Map internal state → `@xyflow/react` `Node[]` / `Edge[]`

- [ ] **Step 3:** Register node type `codegraph: CodegraphNode` in hook or canvas
- [ ] **Step 4:** Run: `npm test -- useGraphCanvas`
- [ ] **Step 5:** Commit: `feat(web): add useGraphCanvas expand orchestration`

---

## Task 7: GraphCanvas container (tasks §2.3, §6.1)

- [ ] **Step 1:** Create `src/components/GraphCanvas.tsx`:

```typescript
type Props = { schema: string; seed: GraphNode | null };

export function GraphCanvas({ schema, seed }: Props) {
  const { nodes, edges, onNodesChange, onNodeClick, ... } = useGraphCanvas(schema, seed);
  if (!seed) return <div data-testid="canvas-empty">Select an entry to begin</div>;
  return (
    <ReactFlow nodes={nodes} edges={edges} onNodeClick={onNodeClick} ...>
      <Background /><Controls />
    </ReactFlow>
  );
}
```

- [ ] **Step 2:** Import `@xyflow/react/dist/style.css` in `main.tsx` or component
- [ ] **Step 3:** Create `src/components/GraphCanvas.test.tsx` — seed renders one node (**6.1**)
- [ ] **Step 4:** Run: `npm test -- GraphCanvas`
- [ ] **Step 5:** Commit: `feat(web): add GraphCanvas React Flow container`

---

## Task 8: Lift schema + App integration (tasks §3.1)

- [ ] **Step 1:** Refactor `SearchBar.tsx` — controlled `schema` + `onSchemaChange` props (remove internal schema state)
- [ ] **Step 2:** Update `SearchBar.test.tsx` for controlled schema
- [ ] **Step 3:** Update `App.tsx`:

```typescript
const [schema, setSchema] = useState('');
// SearchBar schema={schema} onSchemaChange={setSchema}
// GraphCanvas schema={schema} seed={seed}
```

- [ ] **Step 4:** Remove `CanvasPlaceholder` import; delete `CanvasPlaceholder.tsx` + test (or keep test migrated)
- [ ] **Step 5:** Update `App.test.tsx` — adjust for GraphCanvas empty state; existing resolve tests still pass
- [ ] **Step 6:** Commit: `feat(web): wire GraphCanvas and lift schema to App`

---

## Task 9: Integration tests (tasks §6.2–§6.9)

- [ ] **Step 1:** Create `src/components/GraphCanvas.integration.test.tsx` (mock `expandNode`):
  - **6.2** click seed → expand called → second node appears
  - **6.5** two types in graph → different `node-type--*` classes
  - **6.6** slow expand on A → A has loading, B clickable
  - **6.7** expand fail on A → error on A, click B still works

- [ ] **Step 2:** Run: `cd codegraph_web && npm test`
- [ ] **Step 3:** Run: `npm run build`
- [ ] **Step 4:** Commit: `test(web): graph canvas expand integration coverage`

---

## Task 10: OpenSpec tasks sync

- [ ] **Step 1:** Full suite:

```bash
cd codegraph_web && npm test
cd .. && pytest codegraph_server/test_expand_route.py -q
```

- [ ] **Step 2:** Check off all items in `openspec/changes/graph-canvas/tasks.md`
- [ ] **Step 3:** Commit: `docs(openspec): mark graph-canvas tasks complete`

---

## Verification commands (for `/opsx:verify`)

```bash
cd codegraph_web && npm test && npm run build
pytest codegraph_server/test_expand_route.py -q
openspec validate --all --json
```

Manual:

1. `python codegraph_server/app.py` + `cd codegraph_web && npm run dev`
2. Resolve a flowId → seed appears on canvas
3. Click seed → neighbors appear, no duplicate nodes on second expand path
4. Simulate offline → error on clicked node only, Retry works

---

## Commit sequence summary

1. `feat(web): add expand API client and graph edge types`
2. `feat(web): add graph store with dedupe merge`
3. `feat(web): add incremental dagre layout for new nodes`
4. `feat(web): add node type color palette`
5. `feat(web): add CodegraphNode with expand states`
6. `feat(web): add useGraphCanvas expand orchestration`
7. `feat(web): add GraphCanvas React Flow container`
8. `feat(web): wire GraphCanvas and lift schema to App`
9. `test(web): graph canvas expand integration coverage`
10. `docs(openspec): mark graph-canvas tasks complete`
