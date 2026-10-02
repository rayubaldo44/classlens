import type { DemoScenario, DemoStep } from './types'

// DEMO MOCK DATA: UI-only content sourced from docs/DEMO.md. Replace with validated API data.
// No dataset, analysis run, retrieved passage, or provider output is represented here.
export const demoScenario: DemoScenario = {
  subject: 'Science', grade: 'Grade 7', topic: 'Photosynthesis',
  assessmentTitle: 'Photosynthesis free-response check',
  question: 'Explain how plants use sunlight during photosynthesis.',
  expectedConcept: 'Sunlight supplies energy used to produce glucose; it is not itself food.',
  proposedMisconception: 'Sunlight treated as plant food',
  evidence: [
    { id: 'Demo response 01', text: 'Plants eat sunlight.' },
    { id: 'Demo response 02', text: 'Sunlight is the food of plants.' },
    { id: 'Demo response 03', text: 'Plants consume sunlight to grow.' },
  ],
}

export const demoSteps: DemoStep[] = [
  { key: 'dashboard', label: 'Dashboard', path: '/dashboard' },
  { key: 'upload', label: 'Upload assessment', path: '/upload' },
  { key: 'analysis', label: 'Learning gaps', path: '/analysis' },
  { key: 'misconception', label: 'Misconception detail', path: '/misconception' },
  { key: 'intervention', label: 'Intervention review', path: '/intervention' },
  { key: 'results', label: 'Results', path: '/results' },
]
