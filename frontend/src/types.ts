export type RouteKey = 'landing' | 'dashboard' | 'upload' | 'analysis' | 'misconception' | 'intervention' | 'results'

export type DemoStep = { key: RouteKey; label: string; path: string }

export type DemoScenario = {
  subject: string
  grade: string
  topic: string
  assessmentTitle: string
}
