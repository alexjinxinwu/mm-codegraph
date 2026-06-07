import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SchemaSelect } from './SchemaSelect'

describe('SchemaSelect', () => {
  it('renders schema options and fires onChange', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(
      <SchemaSelect schemas={['alpha', 'beta']} value="" onChange={onChange} />,
    )

    await user.selectOptions(screen.getByTestId('schema-select'), 'beta')
    expect(onChange).toHaveBeenCalledWith('beta')
  })
})
