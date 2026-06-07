import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useResolveSearch } from './useResolveSearch'
import * as resolveApi from '../api/resolve'
import type { ResolveResponse } from '../types/graph'

describe('useResolveSearch', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('transitions loading to found with seed', async () => {
    vi.spyOn(resolveApi, 'resolveEntry').mockResolvedValue({
      status: 'found',
      roots: [{ type: 'service_entry', id: 1, title: 'n', subtitle: 't' }],
      candidates: [],
    })

    const { result } = renderHook(() => useResolveSearch())

    await act(async () => {
      await result.current.submit({
        schema: 'S',
        kind: 'commandId',
        value: 'C1',
      })
    })

    await waitFor(() => expect(result.current.phase).toBe('found'))
    expect(result.current.seed).toEqual({
      type: 'service_entry',
      id: 1,
      title: 'n',
      subtitle: 't',
    })
  })

  it('prevents double submit while loading', async () => {
    let resolvePromise!: (value: ResolveResponse) => void
    vi.spyOn(resolveApi, 'resolveEntry').mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePromise = resolve
        }) as ReturnType<typeof resolveApi.resolveEntry>,
    )

    const { result } = renderHook(() => useResolveSearch())

    act(() => {
      void result.current.submit({ schema: 'S', kind: 'commandId', value: 'C1' })
      void result.current.submit({ schema: 'S', kind: 'commandId', value: 'C1' })
    })

    expect(resolveApi.resolveEntry).toHaveBeenCalledTimes(1)

    await act(async () => {
      resolvePromise({
        status: 'found',
        roots: [{ type: 'service_entry', id: 1 }],
        candidates: [],
      })
    })
  })

  it('handles notFound', async () => {
    vi.spyOn(resolveApi, 'resolveEntry').mockResolvedValue({
      status: 'notFound',
      roots: [],
      candidates: [],
    })

    const { result } = renderHook(() => useResolveSearch())

    await act(async () => {
      await result.current.submit({ schema: 'S', kind: 'commandId', value: 'X' })
    })

    expect(result.current.phase).toBe('notFound')
    expect(result.current.seed).toBeNull()
  })

  it('handles multiple candidates', async () => {
    vi.spyOn(resolveApi, 'resolveEntry').mockResolvedValue({
      status: 'multiple',
      roots: [],
      candidates: [
        { type: 'flow', id: 1, title: 'A', subtitle: 'x' },
        { type: 'flow', id: 2, title: 'B', subtitle: 'y' },
      ],
    })

    const { result } = renderHook(() => useResolveSearch())

    await act(async () => {
      await result.current.submit({ schema: 'S', kind: 'flowId', value: 'F1' })
    })

    expect(result.current.phase).toBe('multiple')
    expect(result.current.candidates).toHaveLength(2)
  })

  it('handles fetch error', async () => {
    vi.spyOn(resolveApi, 'resolveEntry').mockRejectedValue(new Error('network'))

    const { result } = renderHook(() => useResolveSearch())

    await act(async () => {
      await result.current.submit({ schema: 'S', kind: 'commandId', value: 'C1' })
    })

    expect(result.current.phase).toBe('error')
  })
})
