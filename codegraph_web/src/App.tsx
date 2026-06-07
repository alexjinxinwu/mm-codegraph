import { useEffect, useState } from 'react'
import { listSchemas } from './api/schemas'
import { AppShell } from './components/AppShell'
import { GraphCanvas } from './components/GraphCanvas'
import { SearchBar } from './components/SearchBar'
import { StatusPanel } from './components/StatusPanel'
import { useResolveSearch } from './hooks/useResolveSearch'
import './App.css'

function App() {
  const [schemas, setSchemas] = useState<string[]>([])
  const [schema, setSchema] = useState('')
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
      searchBar={
        <SearchBar
          schemas={schemas}
          schema={schema}
          onSchemaChange={setSchema}
          loading={loading}
          onSubmit={submit}
        />
      }
      canvas={<GraphCanvas schema={schema} seed={seed} />}
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
