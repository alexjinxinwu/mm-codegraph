import { useCallback, useRef, useState } from 'react'
import { resolveEntry } from '../api/resolve'
import type { GraphNode } from '../types/graph'

export type Phase =
  | 'idle'
  | 'loading'
  | 'found'
  | 'multiple'
  | 'notFound'
  | 'error'

export type ResolveQuery = {
  schema: string
  kind: string
  value: string
}

export function useResolveSearch() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [seed, setSeed] = useState<GraphNode | null>(null)
  const [candidates, setCandidates] = useState<GraphNode[]>([])
  const [lastQuery, setLastQuery] = useState<ResolveQuery | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const inFlight = useRef(false)

  const submit = useCallback(async (query: ResolveQuery) => {
    if (inFlight.current) return
    inFlight.current = true
    setPhase('loading')
    setLastQuery(query)
    setErrorMessage(null)

    try {
      const result = await resolveEntry(query.schema, query.kind, query.value)
      if (result.status === 'found') {
        setSeed(result.roots[0] ?? null)
        setCandidates([])
        setPhase('found')
      } else if (result.status === 'multiple') {
        setSeed(null)
        setCandidates(result.candidates)
        setPhase('multiple')
      } else {
        setSeed(null)
        setCandidates([])
        setPhase('notFound')
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Request failed')
      setPhase('error')
    } finally {
      inFlight.current = false
    }
  }, [])

  const selectCandidate = useCallback((node: GraphNode) => {
    setSeed(node)
    setCandidates([])
    setPhase('found')
  }, [])

  const retry = useCallback(async () => {
    if (lastQuery) {
      await submit(lastQuery)
    }
  }, [lastQuery, submit])

  return {
    phase,
    seed,
    candidates,
    submit,
    selectCandidate,
    retry,
    errorMessage,
    loading: phase === 'loading',
  }
}
