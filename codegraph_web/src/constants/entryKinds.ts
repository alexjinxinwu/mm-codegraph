export const ENTRY_KINDS = [
  { value: 'commandId', label: 'Command ID' },
  { value: 'flowId', label: 'Flow ID' },
] as const

export type EntryKind = (typeof ENTRY_KINDS)[number]['value']
