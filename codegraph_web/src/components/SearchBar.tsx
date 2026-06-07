import { useState, type FormEvent } from 'react'
import type { EntryKind } from '../constants/entryKinds'
import { KindSelect } from './KindSelect'
import { SchemaSelect } from './SchemaSelect'

export type SearchSubmitPayload = {
  schema: string
  kind: EntryKind
  value: string
}

type Props = {
  schemas: string[]
  loading?: boolean
  onSubmit: (payload: SearchSubmitPayload) => void
}

export function SearchBar({ schemas, loading = false, onSubmit }: Props) {
  const [schema, setSchema] = useState('')
  const [kind, setKind] = useState<EntryKind>('commandId')
  const [value, setValue] = useState('')
  const [valueHint, setValueHint] = useState<string | null>(null)

  const schemaMissing = schema === ''
  const valueMissing = value.trim() === ''
  const submitDisabled = schemaMissing || valueMissing || loading

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (schemaMissing) return
    if (valueMissing) {
      setValueHint('Enter a value to search')
      return
    }
    setValueHint(null)
    onSubmit({ schema, kind, value: value.trim() })
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit} aria-busy={loading}>
      <SchemaSelect
        schemas={schemas}
        value={schema}
        onChange={setSchema}
        disabled={loading}
      />
      <KindSelect value={kind} onChange={setKind} disabled={loading} />
      <label className="field" htmlFor="search-value">
        Value
        <input
          id="search-value"
          data-testid="search-value"
          type="text"
          value={value}
          disabled={loading}
          onChange={(e) => {
            setValue(e.target.value)
            if (e.target.value.trim()) setValueHint(null)
          }}
        />
      </label>
      {valueHint && (
        <p className="field-hint" role="alert">
          {valueHint}
        </p>
      )}
      <button
        type="submit"
        disabled={submitDisabled}
        data-validation={schemaMissing ? 'schema-required' : undefined}
      >
        Search
      </button>
    </form>
  )
}
