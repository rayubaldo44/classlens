import type { DemoScenario, DemoStep } from './types'

// Scenario metadata only. Workflow evidence and results come from the API.
export const demoScenario: DemoScenario = {
  subject: 'Science', grade: 'Grade 7', topic: 'Photosynthesis',
  assessmentTitle: 'Photosynthesis free-response check',
}

export const demoSteps: DemoStep[] = [
  { key: 'dashboard', label: 'Dashboard', path: '/dashboard' },
  { key: 'upload', label: 'Upload assessment', path: '/upload' },
  { key: 'analysis', label: 'Learning gaps', path: '/analysis' },
  { key: 'misconception', label: 'Misconception detail', path: '/misconception' },
  { key: 'intervention', label: 'Intervention review', path: '/intervention' },
  { key: 'results', label: 'Results', path: '/results' },
]
