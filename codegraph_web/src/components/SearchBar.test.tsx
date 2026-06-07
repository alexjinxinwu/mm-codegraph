import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { SearchBar } from './SearchBar'

describe('SearchBar', () => {
  it('disables submit when schema is not selected', () => {
    render(
      <SearchBar
        schemas={['S']}
        schema=""
        onSchemaChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled()
  })

  it('does not call onSubmit when value is empty', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    function Wrapper() {
      const [schema, setSchema] = useState('')
      return (
        <SearchBar
          schemas={['S']}
          schema={schema}
          onSchemaChange={setSchema}
          onSubmit={onSubmit}
        />
      )
    }

    render(<Wrapper />)
    await user.selectOptions(screen.getByTestId('schema-select'), 'S')

    expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('calls onSubmit with schema kind and value', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    function Wrapper() {
      const [schema, setSchema] = useState('')
      return (
        <SearchBar
          schemas={['S']}
          schema={schema}
          onSchemaChange={setSchema}
          onSubmit={onSubmit}
        />
      )
    }

    render(<Wrapper />)
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
