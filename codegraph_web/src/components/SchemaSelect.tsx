type Props = {
  schemas: string[]
  value: string
  onChange: (schema: string) => void
  disabled?: boolean
}

export function SchemaSelect({ schemas, value, onChange, disabled }: Props) {
  return (
    <label className="field" htmlFor="schema-select">
      Schema
      <select
        id="schema-select"
        data-testid="schema-select"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select schema…</option>
        {schemas.map((schema) => (
          <option key={schema} value={schema}>
            {schema}
          </option>
        ))}
      </select>
    </label>
  )
}
