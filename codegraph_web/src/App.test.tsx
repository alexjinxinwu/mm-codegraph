import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import * as resolveApi from './api/resolve'
import * as schemasApi from './api/schemas'
import type { ResolveResponse } from './types/graph'

describe('App integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(schemasApi, 'listSchemas').mockResolvedValue(['S'])
  })

  it('found puts root seed on canvas', async () => {
    const user = userEvent.setup()
    vi.spyOn(resolveApi, 'resolveEntry').mockResolvedValue({
      status: 'found',
      roots: [{ type: 'service_entry', id: 12, title: 'Cmd', subtitle: 'command' }],
      candidates: [],
    })

    render(<App />)
    await user.selectOptions(await screen.findByTestId('schema-select'), 'S')
    await user.type(screen.getByTestId('search-value'), 'Cmd1')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(screen.getByTestId('canvas-seed')).toBeInTheDocument()
    })
    expect(screen.getByTestId('seed-type')).toHaveTextContent('service_entry')
    expect(screen.getByTestId('seed-id')).toHaveTextContent('12')
  })

  it('multiple shows candidates with title and subtitle', async () => {
    const user = userEvent.setup()
    vi.spyOn(resolveApi, 'resolveEntry').mockResolvedValue({
      status: 'multiple',
      roots: [],
      candidates: [
        { type: 'flow', id: 1, title: 'F1', subtitle: 'main' },
        { type: 'flow', id: 2, title: 'F2', subtitle: 'draft' },
      ],
    })

    render(<App />)
    await user.selectOptions(await screen.findByTestId('schema-select'), 'S')
    await user.type(screen.getByTestId('search-value'), 'F1')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(screen.getAllByTestId('candidate-title')).toHaveLength(2)
    })
    expect(screen.getAllByTestId('candidate-subtitle')).toHaveLength(2)
  })

  it('selecting candidate sets canvas seed', async () => {
    const user = userEvent.setup()
    vi.spyOn(resolveApi, 'resolveEntry').mockResolvedValue({
      status: 'multiple',
      roots: [],
      candidates: [
        { type: 'flow', id: 2, title: 'F2', subtitle: 'draft' },
      ],
    })

    render(<App />)
    await user.selectOptions(await screen.findByTestId('schema-select'), 'S')
    await user.type(screen.getByTestId('search-value'), 'F1')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await user.click(await screen.findByRole('button', { name: /F2/ }))

    await waitFor(() => {
      expect(screen.getByTestId('seed-id')).toHaveTextContent('2')
    })
  })

  it('notFound shows empty state not error', async () => {
    const user = userEvent.setup()
    vi.spyOn(resolveApi, 'resolveEntry').mockResolvedValue({
      status: 'notFound',
      roots: [],
      candidates: [],
    })

    render(<App />)
    await user.selectOptions(await screen.findByTestId('schema-select'), 'S')
    await user.type(screen.getByTestId('search-value'), 'Missing')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('server error shows error state and retry works', async () => {
    const user = userEvent.setup()
    vi.spyOn(resolveApi, 'resolveEntry')
      .mockRejectedValueOnce(new Error('HTTP 500: boom'))
      .mockResolvedValueOnce({
        status: 'found',
        roots: [{ type: 'flow', id: 3, title: 'F', subtitle: 'main' }],
        candidates: [],
      })

    render(<App />)
    await user.selectOptions(await screen.findByTestId('schema-select'), 'S')
    await user.type(screen.getByTestId('search-value'), 'F1')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Retry' }))

    await waitFor(() => {
      expect(screen.getByTestId('canvas-seed')).toBeInTheDocument()
    })
    expect(resolveApi.resolveEntry).toHaveBeenCalledTimes(2)
  })

  it('blocks submit without schema or empty value', async () => {
    const user = userEvent.setup()
    const resolveSpy = vi.spyOn(resolveApi, 'resolveEntry')

    render(<App />)
    await screen.findByTestId('schema-select')
    expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled()

    await user.selectOptions(screen.getByTestId('schema-select'), 'S')
    expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled()
    expect(resolveSpy).not.toHaveBeenCalled()
  })

  it('prevents duplicate requests while loading', async () => {
    const user = userEvent.setup()
    let resolveFn!: (value: ResolveResponse) => void
    const resolveSpy = vi.spyOn(resolveApi, 'resolveEntry').mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFn = resolve
        }) as ReturnType<typeof resolveApi.resolveEntry>,
    )

    render(<App />)
    await user.selectOptions(await screen.findByTestId('schema-select'), 'S')
    await user.type(screen.getByTestId('search-value'), 'Cmd1')

    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(screen.getByTestId('loading-state')).toBeInTheDocument()
    expect(resolveSpy).toHaveBeenCalledTimes(1)

    resolveFn({
      status: 'found',
      roots: [{ type: 'service_entry', id: 1 }],
      candidates: [],
    })

    await waitFor(() => {
      expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument()
    })
  })
})
