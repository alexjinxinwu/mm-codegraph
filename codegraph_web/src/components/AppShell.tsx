import type { ReactNode } from 'react'
import './AppShell.css'

type Props = {
  searchBar: ReactNode
  canvas: ReactNode
  statusPanel: ReactNode
}

export function AppShell({ searchBar, canvas, statusPanel }: Props) {
  return (
    <div className="app-shell" data-testid="app-shell">
      <header className="app-shell__search" data-testid="search-bar">
        {searchBar}
      </header>
      <main className="app-shell__canvas" data-testid="canvas">
        {canvas}
      </main>
      <aside className="app-shell__status" data-testid="status-panel">
        {statusPanel}
      </aside>
    </div>
  )
}
