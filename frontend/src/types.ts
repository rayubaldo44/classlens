export type RouteKey = 'dashboard' | 'upload' | 'analysis' | 'misconception' | 'intervention' | 'results'

export type DemoStep = { key: RouteKey; label: string; path: string }
export type EvidenceResponse = { id: string; text: string }

export type DemoScenario = {
  subject: string
  grade: string
  topic: string
  assessmentTitle: string
  question: string
  expectedConcept: string
  proposedMisconception: string
  evidence: EvidenceResponse[]
}
