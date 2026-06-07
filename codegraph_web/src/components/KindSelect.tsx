import { ENTRY_KINDS } from '../constants/entryKinds'
import type { EntryKind } from '../constants/entryKinds'

type Props = {
  value: EntryKind
  onChange: (kind: EntryKind) => void
  disabled?: boolean
}

export function KindSelect({ value, onChange, disabled }: Props) {
  return (
    <label className="field" htmlFor="kind-select">
      Kind
      <select
        id="kind-select"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as EntryKind)}
      >
        {ENTRY_KINDS.map((kind) => (
          <option key={kind.value} value={kind.value}>
            {kind.label}
          </option>
        ))}
      </select>
    </label>
  )
}
