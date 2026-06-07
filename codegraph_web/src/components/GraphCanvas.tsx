import { ReactFlowProvider } from '@xyflow/react'
import {
  Background,
  Controls,
  ReactFlow,
} from '@xyflow/react'
import type { GraphNode } from '../types/graph'
import { useGraphCanvas } from '../graph/useGraphCanvas'
import { codegraphNodeTypes } from './CodegraphNode'
import './graphCanvas.css'

type Props = {
  schema: string
  seed: GraphNode | null
}

function GraphCanvasInner({ schema, seed }: Props) {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onNodeClick,
  } = useGraphCanvas(schema, seed)

  return (
    <div className="codegraph-canvas" data-testid="graph-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={codegraphNodeTypes}
        fitView
        nodesDraggable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}

export function GraphCanvas({ schema, seed }: Props) {
  if (!seed) {
    return (
      <div className="canvas-empty" data-testid="canvas-empty">
        Select an entry to begin
      </div>
    )
  }

  return (
    <ReactFlowProvider>
      <GraphCanvasInner schema={schema} seed={seed} />
    </ReactFlowProvider>
  )
}
