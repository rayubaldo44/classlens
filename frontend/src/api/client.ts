import { RequestTimeoutError, withAbortTimeout } from './requestReliability'
import {
  isAnalysisResponse,
  isAssessmentPreview,
  isFollowUpComparison,
  isMaterialIngestionResponse,
  isMaterialRetrievalResponse,
  isRemediationGenerationResponse,
  isRemediationRecord,
} from './contracts'

export type HealthResponse = { status: 'ok'; service: 'classlens-api' }
export type NormalizedResponse = { row_number: number; student_id: string; question_id: string; question: string; answer: string; correct_answer: string; answer_status: 'answered' | 'blank'; is_correct: boolean }
export type AssessmentPreview = {
  status: 'validated'
  data_label: 'teacher_upload' | 'synthetic_demo'
  filename: string
  assessment: { title: string; subject: string; grade_level: string; topic: string }
  summary: { response_count: number; answered_count: number; blank_count: number; student_count: number; question_count: number; correct_count: number; incorrect_count: number }
  sample_responses: NormalizedResponse[]
}
export type RepresentativeResponse = { student_id: string; answer: string; similarity_to_medoid: number }
export type MisconceptionGroup = {
  group_id: string
  provisional_label: string
  interpretation_status: 'not_requested'
  question_id: string
  question: string
  correct_answer: string
  support_count: number
  eligible_response_count: number
  member_student_ids: string[]
  representative_responses: RepresentativeResponse[]
  coherence: number
}
export type AnalysisResponse = {
  assessment_id: string
  analysis_id: string
  status: 'completed' | 'insufficient_data'
  data_label: 'teacher_upload' | 'synthetic_demo'
  filename: string
  assessment: AssessmentPreview['assessment']
  summary: {
    response_count: number
    answered_count: number
    blank_count: number
    correct_count: number
    eligible_incorrect_count: number
    grouped_response_count: number
    outlier_count: number
    question_count: number
    group_count: number
  }
  embedding: { model_id: string; dimension: number; preprocessing: 'answer_only_v1' }
  grouping: { algorithm: 'complete_link_cosine_v1'; similarity_threshold: number; minimum_support: number }
  groups: MisconceptionGroup[]
  message: string | null
}
export type LearningMaterial = {
  material_id: string
  title: string
  filename: string
  source_kind: 'teacher_upload' | 'synthetic_demo'
  content_hash: string
  chunk_count: number
  chunk_size_chars: number
  chunk_overlap_chars: number
  embedding_model: string
  embedding_dimension: number
}
export type MaterialIngestionResponse = {
  status: 'ready'
  material: LearningMaterial
  message: string
}
export type MaterialRetrievalContext = {
  group_id: string
  question_id: string
  question: string
  correct_answer: string
  representative_answers: string[]
}
export type MaterialRetrievalResponse = {
  status: 'retrieved' | 'insufficient_relevant_context'
  group_id: string
  material: LearningMaterial
  retrieval: {
    algorithm: 'cosine_similarity_v1'
    top_k: number
    minimum_relevance_score: number
    embedding_model: string
  }
  results: { chunk_id: string; chunk_index: number; text: string; similarity: number; start_char: number; end_char: number }[]
  message: string | null
}
export type FollowUpQuestion = { prompt: string; expected_answer: string }
export type EditableRemediationContent = {
  misconception_summary: string
  learning_objective: string
  teacher_explanation: string
  corrected_concept: string
  activity: string
  analogy: string | null
  follow_up_questions: FollowUpQuestion[]
}
export type RemediationContent = EditableRemediationContent & { source_references: string[] }
export type RemediationRecord = {
  remediation_id: string
  status: 'generated' | 'approved' | 'rejected'
  analysis_id: string
  group_id: string
  provider: string
  model: string
  prompt_version: 'grounded_remediation_v1'
  generated_content: RemediationContent
  content: RemediationContent
  sources: {
    material_id: string
    material_title: string
    filename: string
    chunk_id: string
    chunk_index: number
    text: string
    similarity: number
    start_char: number
    end_char: number
  }[]
  review_notes: string | null
  created_at: string
  updated_at: string
}
export type RemediationGenerationRequest = {
  generation_request_id: string
  analysis_id: string
  grade_level: string
  subject: string
  topic: string
  misconception: {
    group_id: string
    provisional_label: string
    question_id: string
    question: string
    correct_answer: string
    support_count: number
    eligible_response_count: number
    representative_responses: RepresentativeResponse[]
  }
  retrieval: MaterialRetrievalResponse
}
export type RemediationGenerationResponse = {
  status: 'generated' | 'insufficient_context'
  remediation: RemediationRecord | null
  message: string | null
}
export type RemediationReviewRequest = {
  action: 'save' | 'approve' | 'reject'
  edited_content?: EditableRemediationContent
  review_notes?: string
}
export type FollowUpComparisonLink = {
  baseline_analysis_id: string
  group_id: string
  remediation_id: string
}
export type AssessmentResultSnapshot = {
  analysis_id: string
  assessment_title: string
  filename: string
  answered_students: number
  correct_students: number
  affected_students: number
  misconception_prevalence_percent: number
}
export type FollowUpComparisonRecord = {
  comparison_id: string
  status: 'completed' | 'insufficient_data'
  data_label: 'teacher_upload' | 'synthetic_demo'
  subject: string
  grade_level: string
  topic: string
  question_id: string
  question: string
  misconception_label: string
  trace: {
    baseline_assessment_id: string
    follow_up_assessment_id: string
    baseline_analysis_id: string
    follow_up_analysis_id: string
    baseline_group_id: string
    follow_up_group_id: string | null
    remediation_id: string
    remediation_status: 'approved'
    comparison_method: 'same_question_member_overlap_v1'
  } | null
  metrics: {
    before: AssessmentResultSnapshot
    after: AssessmentResultSnapshot
    matched_answered_students: number
    missing_follow_up_students: number
    percentage_point_reduction: number
    correct_percentage_point_change: number
    transitions: {
      baseline_affected_students: number
      resolved_correct: number
      changed_but_still_incorrect: number
      still_struggling: number
      missing_from_baseline_group: number
      new_affected_students: number
    }
  } | null
  message: string | null
  created_at: string
}

export class ApiError extends Error {
  readonly code: string

  constructor(code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

export const NETWORK_FAILURE_HINT = 'The browser could not reach the API. It may be stopped, or this origin may be blocked by CORS.'
export const REMEDIATION_REQUEST_TIMEOUT_MS = 70_000

const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Record<string, unknown>
  return candidate.status === 'ok' && candidate.service === 'classlens-api'
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${apiUrl}/health`, { headers: { Accept: 'application/json' }, signal })
  if (!response.ok) throw new Error(`Health request failed with status ${response.status}.`)

  const data: unknown = await response.json()
  if (!isHealthResponse(data)) throw new Error('Health response did not match the ClassLens API contract.')
  return data
}

async function readPreviewResponse(response: Response): Promise<AssessmentPreview> {
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = typeof data === 'object' && data !== null && 'error' in data ? (data as { error?: { code?: unknown; message?: unknown } }).error : undefined
    throw new ApiError(typeof error?.code === 'string' ? error.code : 'request_failed', typeof error?.message === 'string' ? error.message : `Upload failed with status ${response.status}.`)
  }
  if (!isAssessmentPreview(data)) throw new ApiError('invalid_response', 'The assessment preview response was not valid.')
  return data
}

async function readAnalysisResponse(response: Response): Promise<AnalysisResponse> {
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = typeof data === 'object' && data !== null && 'error' in data ? (data as { error?: { code?: unknown; message?: unknown } }).error : undefined
    throw new ApiError(typeof error?.code === 'string' ? error.code : 'request_failed', typeof error?.message === 'string' ? error.message : `Analysis failed with status ${response.status}.`)
  }
  if (!isAnalysisResponse(data)) throw new ApiError('invalid_response', 'The assessment analysis response was not valid.')
  return data
}

export async function uploadAssessment(file: File): Promise<AssessmentPreview> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${apiUrl}/api/v1/assessments/preview`, { method: 'POST', body: form })
  return readPreviewResponse(response)
}

export async function getPhotosynthesisDemo(): Promise<AssessmentPreview> {
  const response = await fetch(`${apiUrl}/api/v1/assessments/demo/photosynthesis/preview`, { headers: { Accept: 'application/json' } })
  return readPreviewResponse(response)
}

export async function analyzeAssessment(file: File, signal?: AbortSignal): Promise<AnalysisResponse> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${apiUrl}/api/v1/assessments/analyze`, { method: 'POST', body: form, signal })
  return readAnalysisResponse(response)
}

export async function analyzePhotosynthesisDemo(signal?: AbortSignal): Promise<AnalysisResponse> {
  const response = await fetch(`${apiUrl}/api/v1/assessments/demo/photosynthesis/analysis`, { headers: { Accept: 'application/json' }, signal })
  return readAnalysisResponse(response)
}

export async function getAnalysis(analysisId: string): Promise<AnalysisResponse> {
  const response = await fetch(`${apiUrl}/api/v1/assessments/analyses/${encodeURIComponent(analysisId)}`, {
    headers: { Accept: 'application/json' },
  })
  return readAnalysisResponse(response)
}

async function readMaterialResponse(response: Response): Promise<MaterialIngestionResponse> {
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = typeof data === 'object' && data !== null && 'error' in data ? (data as { error?: { code?: unknown; message?: unknown } }).error : undefined
    throw new ApiError(typeof error?.code === 'string' ? error.code : 'request_failed', typeof error?.message === 'string' ? error.message : `Material ingestion failed with status ${response.status}.`)
  }
  if (!isMaterialIngestionResponse(data)) {
    throw new ApiError('invalid_response', 'The learning material response was not valid.')
  }
  return data
}

export async function ingestLearningMaterial(file: File): Promise<MaterialIngestionResponse> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${apiUrl}/api/v1/learning-materials/ingest`, { method: 'POST', body: form })
  return readMaterialResponse(response)
}

export async function ingestPhotosynthesisDemoMaterial(): Promise<MaterialIngestionResponse> {
  const response = await fetch(`${apiUrl}/api/v1/learning-materials/demo/photosynthesis/ingest`, { method: 'POST' })
  return readMaterialResponse(response)
}

export async function retrieveMaterialForGroup(
  materialId: string,
  context: MaterialRetrievalContext,
  signal?: AbortSignal,
): Promise<MaterialRetrievalResponse> {
  const response = await fetch(`${apiUrl}/api/v1/learning-materials/${encodeURIComponent(materialId)}/retrieve`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(context),
    signal,
  })
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = typeof data === 'object' && data !== null && 'error' in data ? (data as { error?: { code?: unknown; message?: unknown } }).error : undefined
    throw new ApiError(typeof error?.code === 'string' ? error.code : 'request_failed', typeof error?.message === 'string' ? error.message : `Material retrieval failed with status ${response.status}.`)
  }
  if (!isMaterialRetrievalResponse(data)) {
    throw new ApiError('invalid_response', 'The material retrieval response was not valid.')
  }
  return data
}

async function readApiResponse<T>(
  response: Response,
  isValid: (data: unknown) => data is T,
  fallback: string,
  invalidResponseMessage: string,
): Promise<T> {
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = typeof data === 'object' && data !== null && 'error' in data ? (data as { error?: { code?: unknown; message?: unknown } }).error : undefined
    throw new ApiError(typeof error?.code === 'string' ? error.code : 'request_failed', typeof error?.message === 'string' ? error.message : fallback)
  }
  if (!isValid(data)) throw new ApiError('invalid_response', invalidResponseMessage)
  return data
}

export async function generateRemediation(request: RemediationGenerationRequest): Promise<RemediationGenerationResponse> {
  try {
    return await withAbortTimeout(REMEDIATION_REQUEST_TIMEOUT_MS, async (signal) => {
      const response = await fetch(`${apiUrl}/api/v1/remediations`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal,
      })
      return readApiResponse<RemediationGenerationResponse>(
        response,
        isRemediationGenerationResponse,
        `Remediation generation failed with status ${response.status}.`,
        'The API returned incomplete remediation data. Your evidence is unchanged; retry generation or restart this workflow.',
      )
    })
  } catch (error: unknown) {
    if (error instanceof RequestTimeoutError) {
      throw new ApiError(
        'request_timeout',
        'Generation reached the 70-second browser limit. Your evidence is still available; retrying will reuse this request and will not create a duplicate draft.',
      )
    }
    throw error
  }
}

export async function getRemediation(remediationId: string): Promise<RemediationRecord> {
  const response = await fetch(`${apiUrl}/api/v1/remediations/${encodeURIComponent(remediationId)}`, { headers: { Accept: 'application/json' } })
  return readApiResponse<RemediationRecord>(
    response,
    isRemediationRecord,
    `Remediation retrieval failed with status ${response.status}.`,
    'The saved remediation response was incomplete. Reload the workflow from its analysis evidence.',
  )
}

export async function reviewRemediation(remediationId: string, request: RemediationReviewRequest): Promise<RemediationRecord> {
  const response = await fetch(`${apiUrl}/api/v1/remediations/${encodeURIComponent(remediationId)}`, {
    method: 'PATCH',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return readApiResponse<RemediationRecord>(
    response,
    isRemediationRecord,
    `Remediation review failed with status ${response.status}.`,
    'The API returned an incomplete teacher-review record. Your edits remain on this screen; try saving again.',
  )
}

export async function submitFollowUpComparison(
  file: File,
  link: FollowUpComparisonLink,
): Promise<FollowUpComparisonRecord> {
  const form = new FormData()
  form.append('file', file)
  form.append('baseline_analysis_id', link.baseline_analysis_id)
  form.append('group_id', link.group_id)
  form.append('remediation_id', link.remediation_id)
  const response = await fetch(`${apiUrl}/api/v1/results`, { method: 'POST', body: form })
  return readApiResponse<FollowUpComparisonRecord>(
    response,
    isFollowUpComparison,
    `Follow-up comparison failed with status ${response.status}.`,
    'The API returned incomplete follow-up results. Retry the comparison from the approved intervention.',
  )
}

export async function submitPhotosynthesisDemoComparison(
  link: FollowUpComparisonLink,
): Promise<FollowUpComparisonRecord> {
  const response = await fetch(`${apiUrl}/api/v1/results/demo/photosynthesis`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(link),
  })
  return readApiResponse<FollowUpComparisonRecord>(
    response,
    isFollowUpComparison,
    `Demo follow-up comparison failed with status ${response.status}.`,
    'The API returned incomplete demo follow-up results. Retry the comparison from the approved intervention.',
  )
}

export async function getFollowUpComparison(comparisonId: string): Promise<FollowUpComparisonRecord> {
  const response = await fetch(`${apiUrl}/api/v1/results/${encodeURIComponent(comparisonId)}`, {
    headers: { Accept: 'application/json' },
  })
  return readApiResponse<FollowUpComparisonRecord>(
    response,
    isFollowUpComparison,
    `Follow-up results retrieval failed with status ${response.status}.`,
    'The saved follow-up result was incomplete. Rerun the comparison from the approved intervention.',
  )
}
