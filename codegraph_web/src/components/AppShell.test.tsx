import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AppShell } from './AppShell'

describe('AppShell', () => {
  it('renders three persistent regions', () => {
    render(
      <AppShell
        searchBar={<span>Search</span>}
        canvas={<span>Canvas</span>}
        statusPanel={<span>Status</span>}
      />,
    )

    expect(screen.getByTestId('search-bar')).toBeInTheDocument()
    expect(screen.getByTestId('canvas')).toBeInTheDocument()
    expect(screen.getByTestId('status-panel')).toBeInTheDocument()
  })

  it('keeps all regions accessible at narrow viewport', () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 375,
    })

    render(
      <AppShell
        searchBar={<span>Search</span>}
        canvas={<span>Canvas</span>}
        statusPanel={<span>Status</span>}
      />,
    )

    expect(screen.getByTestId('search-bar')).toBeVisible()
    expect(screen.getByTestId('canvas')).toBeVisible()
    expect(screen.getByTestId('status-panel')).toBeVisible()
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      document.documentElement.clientWidth + 1,
    )
  })
})
