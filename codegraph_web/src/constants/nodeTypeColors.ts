export const NODE_TYPES = [
  'service_entry',
  'flow',
  'logic',
  'bean',
  'state',
  'flow_task',
  'activity',
  'transition',
  'logic_step',
  'bridge',
  'java_class',
  'interceptor',
  'java_method',
  'module_parameter',
] as const

export const NODE_TYPE_COLORS: Record<string, string> = {
  service_entry: '#2563eb',
  flow: '#7c3aed',
  logic: '#059669',
  bean: '#d97706',
  state: '#db2777',
  flow_task: '#0891b2',
  activity: '#65a30d',
  transition: '#9333ea',
  logic_step: '#0d9488',
  bridge: '#ea580c',
  java_class: '#4f46e5',
  interceptor: '#c026d3',
  java_method: '#0284c7',
  module_parameter: '#64748b',
}

export function colorForNodeType(type: string): string {
  return NODE_TYPE_COLORS[type] ?? '#475569'
}
