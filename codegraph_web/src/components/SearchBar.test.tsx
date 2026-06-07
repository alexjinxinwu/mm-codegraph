import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SearchBar } from './SearchBar'

describe('SearchBar', () => {
  it('disables submit when schema is not selected', () => {
    render(<SearchBar schemas={['S']} onSubmit={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Search' })).toHaveAttribute(
      'data-validation',
      'schema-required',
    )
  })

  it('does not call onSubmit when value is empty', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<SearchBar schemas={['S']} onSubmit={onSubmit} />)
    await user.selectOptions(screen.getByTestId('schema-select'), 'S')

    const button = screen.getByRole('button', { name: 'Search' })
    expect(button).toBeDisabled()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('calls onSubmit with schema kind and value', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<SearchBar schemas={['S']} onSubmit={onSubmit} />)
    await user.selectOptions(screen.getByTestId('schema-select'), 'S')
    await user.type(screen.getByTestId('search-value'), 'Cmd1')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    expect(onSubmit).toHaveBeenCalledWith({
      schema: 'S',
      kind: 'commandId',
      value: 'Cmd1',
    })
  })
})
