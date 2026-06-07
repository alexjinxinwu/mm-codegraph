import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { ExpandPhase } from '../types/graph'
import { colorForNodeType } from '../constants/nodeTypeColors'
import './graphCanvas.css'

export type CodegraphNodeData = {
  title?: string | null
  subtitle?: string | null
  nodeType: string
  nodeId: number
  expanded?: boolean
  phase: ExpandPhase
  onRetry?: () => void
}

function CodegraphNodeComponent({ data }: NodeProps) {
  const nodeData = data as CodegraphNodeData
  const borderColor = colorForNodeType(nodeData.nodeType)

  return (
    <div
      className={`codegraph-node node-type--${nodeData.nodeType}${nodeData.phase === 'error' ? ' codegraph-node--error' : ''}${nodeData.expanded ? ' codegraph-node--expanded' : ''}`}
      style={{ borderColor }}
      data-testid="graph-node"
    >
      <Handle type="target" position={Position.Left} />
      <div className="codegraph-node__badge" data-testid="seed-type">
        {nodeData.nodeType}
      </div>
      <div className="codegraph-node__title" data-testid="seed-title">
        {nodeData.title ?? nodeData.nodeType}
      </div>
      <div className="codegraph-node__id" data-testid="seed-id">
        {nodeData.nodeId}
      </div>
      {nodeData.subtitle != null && nodeData.subtitle !== '' && (
        <div className="codegraph-node__subtitle" data-testid="seed-subtitle">
          {nodeData.subtitle}
        </div>
      )}
      {nodeData.expanded && (
        <span className="codegraph-node__expanded" data-testid="node-expanded">
          expanded
        </span>
      )}
      {nodeData.phase === 'loading' && (
        <div className="codegraph-node__overlay" data-testid="node-loading">
          Loading…
        </div>
      )}
      {nodeData.phase === 'error' && (
        <div className="codegraph-node__overlay codegraph-node__overlay--error" data-testid="node-error">
          <span>Expand failed</span>
          <button type="button" onClick={() => nodeData.onRetry?.()}>
            Retry
          </button>
        </div>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

export const CodegraphNode = memo(CodegraphNodeComponent)

export const codegraphNodeTypes = {
  codegraph: CodegraphNode,
}
