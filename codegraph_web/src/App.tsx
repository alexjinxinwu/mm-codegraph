import { useEffect, useState } from 'react'
import { listSchemas } from './api/schemas'
import { AppShell } from './components/AppShell'
import { CanvasPlaceholder } from './components/CanvasPlaceholder'
import { SearchBar } from './components/SearchBar'
import { StatusPanel } from './components/StatusPanel'
import { useResolveSearch } from './hooks/useResolveSearch'
import './App.css'

function App() {
  const [schemas, setSchemas] = useState<string[]>([])
  const {
    phase,
    seed,
    candidates,
    submit,
    selectCandidate,
    retry,
    errorMessage,
    loading,
  } = useResolveSearch()

  useEffect(() => {
    listSchemas()
      .then(setSchemas)
      .catch(() => setSchemas([]))
  }, [])

  return (
    <AppShell
      searchBar={<SearchBar schemas={schemas} loading={loading} onSubmit={submit} />}
      canvas={<CanvasPlaceholder seed={seed} />}
      statusPanel={
        <StatusPanel
          phase={phase}
          candidates={candidates}
          errorMessage={errorMessage}
          onSelectCandidate={selectCandidate}
          onRetry={retry}
        />
      }
    />
  )
}

export default App
