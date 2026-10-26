import type {
  AnalysisResponse,
  AssessmentPreview,
  FollowUpComparisonRecord,
  MaterialIngestionResponse,
  MaterialRetrievalResponse,
  RemediationGenerationResponse,
  RemediationRecord,
  GroupReviewResponse,
} from './client'

type JsonObject = Record<string, unknown>

const isObject = (value: unknown): value is JsonObject => typeof value === 'object' && value !== null && !Array.isArray(value)
const isString = (value: unknown): value is string => typeof value === 'string'
const isNonEmptyString = (value: unknown): value is string => isString(value) && value.length > 0
const isNullableString = (value: unknown): value is string | null => value === null || isString(value)
const isFiniteNumber = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const isCount = (value: unknown): value is number => Number.isInteger(value) && (value as number) >= 0
const isPositiveInteger = (value: unknown): value is number => Number.isInteger(value) && (value as number) > 0
const isBoolean = (value: unknown): value is boolean => typeof value === 'boolean'
const isArrayOf = (value: unknown, predicate: (item: unknown) => boolean): value is unknown[] => Array.isArray(value) && value.every(predicate)
const isDateTime = (value: unknown): value is string => isString(value) && !Number.isNaN(Date.parse(value))

const isAssessmentMetadata = (value: unknown) => isObject(value)
  && isNonEmptyString(value.title)
  && isNonEmptyString(value.subject)
  && isNonEmptyString(value.grade_level)
  && isNonEmptyString(value.topic)

const isNormalizedResponse = (value: unknown) => isObject(value)
  && isPositiveInteger(value.row_number)
  && isNonEmptyString(value.student_id)
  && isNonEmptyString(value.question_id)
  && isNonEmptyString(value.question)
  && isString(value.answer)
  && isNonEmptyString(value.correct_answer)
  && (value.answer_status === 'answered' || value.answer_status === 'blank')
  && isBoolean(value.is_correct)

const isAssessmentSummary = (value: unknown) => isObject(value)
  && isCount(value.response_count)
  && isCount(value.answered_count)
  && isCount(value.blank_count)
  && isCount(value.student_count)
  && isCount(value.question_count)
  && isCount(value.correct_count)
  && isCount(value.incorrect_count)

export const isAssessmentPreview = (value: unknown): value is AssessmentPreview => isObject(value)
  && value.status === 'validated'
  && (value.data_label === 'teacher_upload' || value.data_label === 'synthetic_demo')
  && isNonEmptyString(value.filename)
  && isAssessmentMetadata(value.assessment)
  && isAssessmentSummary(value.summary)
  && isArrayOf(value.sample_responses, isNormalizedResponse)

const isRepresentativeResponse = (value: unknown) => isObject(value)
  && isNonEmptyString(value.student_id)
  && isNonEmptyString(value.answer)
  && isFiniteNumber(value.similarity_to_medoid)

const isMisconceptionGroup = (value: unknown) => isObject(value)
  && isNonEmptyString(value.group_id)
  && isNonEmptyString(value.provisional_label)
  && (value.interpretation_status === 'not_requested' || value.interpretation_status === 'completed' || value.interpretation_status === 'fallback')
  && isNonEmptyString(value.question_id)
  && isNonEmptyString(value.question)
  && isNonEmptyString(value.correct_answer)
  && isPositiveInteger(value.support_count)
  && isPositiveInteger(value.eligible_response_count)
  && isArrayOf(value.member_student_ids, isNonEmptyString)
  && isArrayOf(value.representative_responses, isRepresentativeResponse)
  && isFiniteNumber(value.coherence)

const isAnalysisSummary = (value: unknown) => isObject(value)
  && isCount(value.response_count)
  && isCount(value.answered_count)
  && isCount(value.blank_count)
  && isCount(value.correct_count)
  && isCount(value.eligible_incorrect_count)
  && isCount(value.grouped_response_count)
  && isCount(value.outlier_count)
  && isCount(value.question_count)
  && isCount(value.group_count)

export const isAnalysisResponse = (value: unknown): value is AnalysisResponse => {
  if (!isObject(value) || !Array.isArray(value.groups)) return false
  return isNonEmptyString(value.assessment_id)
    && isNonEmptyString(value.analysis_id)
    && (value.status === 'completed' || value.status === 'insufficient_data')
    && (value.data_label === 'teacher_upload' || value.data_label === 'synthetic_demo')
    && isNonEmptyString(value.filename)
    && isAssessmentMetadata(value.assessment)
    && isAnalysisSummary(value.summary)
    && isObject(value.embedding)
    && isNonEmptyString(value.embedding.model_id)
    && isPositiveInteger(value.embedding.dimension)
    && value.embedding.preprocessing === 'answer_only_v1'
    && isObject(value.grouping)
    && value.grouping.algorithm === 'complete_link_cosine_v1'
    && isFiniteNumber(value.grouping.similarity_threshold)
    && isPositiveInteger(value.grouping.minimum_support)
    && isArrayOf(value.groups, isMisconceptionGroup)
    && (value.summary as JsonObject).group_count === value.groups.length
    && isNullableString(value.message)
}

const isReviewedGroup = (value: unknown) => isObject(value)
  && isNonEmptyString(value.reviewed_group_id)
  && isNonEmptyString(value.display_label)
  && (value.status === 'active' || value.status === 'dismissed')
  && isArrayOf(value.source_group_ids, isNonEmptyString) && value.source_group_ids.length > 0
  && new Set(value.source_group_ids).size === value.source_group_ids.length
  && isNonEmptyString(value.question_id) && isNonEmptyString(value.question) && isNonEmptyString(value.correct_answer)
  && isPositiveInteger(value.support_count) && isPositiveInteger(value.eligible_response_count)
  && isArrayOf(value.member_student_ids, isNonEmptyString)
  && isArrayOf(value.representative_responses, isRepresentativeResponse)
  && (value.coherence === null || isFiniteNumber(value.coherence))

const isReviewState = (value: unknown) => isObject(value)
  && isNonEmptyString(value.analysis_id) && isCount(value.revision)
  && isArrayOf(value.groups, isReviewedGroup)

const isReviewEvent = (value: unknown) => isObject(value)
  && isNonEmptyString(value.event_id) && isNonEmptyString(value.analysis_id) && isPositiveInteger(value.sequence)
  && ['rename', 'merge', 'dismiss', 'restore'].includes(String(value.action))
  && isArrayOf(value.source_group_ids, isNonEmptyString) && value.source_group_ids.length > 0
  && isNonEmptyString(value.resulting_reviewed_group_id)
  && (value.previous_state === null || isReviewState(value.previous_state))
  && isReviewState(value.next_state) && isNullableString(value.review_note) && isDateTime(value.created_at)

export const isGroupReviewResponse = (value: unknown): value is GroupReviewResponse => {
  if (!isObject(value) || !isCount(value.revision)
    || !isArrayOf(value.active_groups, isReviewedGroup)
    || !isArrayOf(value.dismissed_groups, isReviewedGroup)
    || !isArrayOf(value.locked_group_ids, isNonEmptyString)
    || !isArrayOf(value.events, isReviewEvent)) return false
  if (!isNonEmptyString(value.analysis_id)) return false
  if ((value.active_groups as JsonObject[]).some((group) => group.status !== 'active')) return false
  if ((value.dismissed_groups as JsonObject[]).some((group) => group.status !== 'dismissed')) return false
  return value.events.every((event, index) => {
    const item = event as JsonObject
    return item.analysis_id === value.analysis_id && item.sequence === index + 1
  })
}

const isLearningMaterial = (value: unknown) => isObject(value)
  && isNonEmptyString(value.material_id)
  && isNonEmptyString(value.title)
  && isNonEmptyString(value.filename)
  && (value.source_kind === 'teacher_upload' || value.source_kind === 'synthetic_demo')
  && isNonEmptyString(value.content_hash)
  && isPositiveInteger(value.chunk_count)
  && isPositiveInteger(value.chunk_size_chars)
  && isCount(value.chunk_overlap_chars)
  && isNonEmptyString(value.embedding_model)
  && isPositiveInteger(value.embedding_dimension)

export const isMaterialIngestionResponse = (value: unknown): value is MaterialIngestionResponse => isObject(value)
  && value.status === 'ready'
  && isLearningMaterial(value.material)
  && isString(value.message)

const isRetrievedChunk = (value: unknown) => isObject(value)
  && isNonEmptyString(value.chunk_id)
  && isCount(value.chunk_index)
  && isNonEmptyString(value.text)
  && isFiniteNumber(value.similarity)
  && isCount(value.start_char)
  && isPositiveInteger(value.end_char)
  && value.end_char > value.start_char

export const isMaterialRetrievalResponse = (value: unknown): value is MaterialRetrievalResponse => {
  if (!isObject(value) || !Array.isArray(value.results)) return false
  const hasConsistentStatus = value.status === 'retrieved' ? value.results.length > 0
    : value.status === 'insufficient_relevant_context' && value.results.length === 0
  return hasConsistentStatus
    && isNonEmptyString(value.group_id)
    && isArrayOf(value.source_group_ids, isNonEmptyString) && value.source_group_ids.length > 0
    && isLearningMaterial(value.material)
    && isObject(value.retrieval)
    && value.retrieval.algorithm === 'cosine_similarity_v1'
    && isPositiveInteger(value.retrieval.top_k)
    && isFiniteNumber(value.retrieval.minimum_relevance_score)
    && isNonEmptyString(value.retrieval.embedding_model)
    && isArrayOf(value.results, isRetrievedChunk)
    && isNullableString(value.message)
}

const isFollowUpQuestion = (value: unknown) => isObject(value)
  && isNonEmptyString(value.prompt)
  && isNonEmptyString(value.expected_answer)

const isRemediationContent = (value: unknown) => isObject(value)
  && isNonEmptyString(value.misconception_summary)
  && isNonEmptyString(value.learning_objective)
  && isNonEmptyString(value.teacher_explanation)
  && isNonEmptyString(value.corrected_concept)
  && isNonEmptyString(value.activity)
  && isNullableString(value.analogy)
  && isArrayOf(value.follow_up_questions, isFollowUpQuestion)
  && value.follow_up_questions.length >= 1
  && value.follow_up_questions.length <= 3
  && isArrayOf(value.source_references, isNonEmptyString)
  && value.source_references.length > 0

const isRemediationSource = (value: unknown) => isObject(value)
  && isNonEmptyString(value.material_id)
  && isNonEmptyString(value.material_title)
  && isNonEmptyString(value.filename)
  && isNonEmptyString(value.chunk_id)
  && isCount(value.chunk_index)
  && isNonEmptyString(value.text)
  && isFiniteNumber(value.similarity)
  && isCount(value.start_char)
  && isPositiveInteger(value.end_char)
  && value.end_char > value.start_char

export const isRemediationRecord = (value: unknown): value is RemediationRecord => isObject(value)
  && isNonEmptyString(value.remediation_id)
  && (value.status === 'generated' || value.status === 'approved' || value.status === 'rejected')
  && isNonEmptyString(value.analysis_id)
  && isNonEmptyString(value.group_id)
  && isArrayOf(value.source_group_ids, isNonEmptyString) && value.source_group_ids.length > 0
  && isNonEmptyString(value.provider)
  && isNonEmptyString(value.model)
  && value.prompt_version === 'grounded_remediation_v1'
  && isRemediationContent(value.generated_content)
  && isRemediationContent(value.content)
  && isArrayOf(value.sources, isRemediationSource)
  && value.sources.length > 0
  && isNullableString(value.review_notes)
  && isDateTime(value.created_at)
  && isDateTime(value.updated_at)

export const isRemediationGenerationResponse = (value: unknown): value is RemediationGenerationResponse => {
  if (!isObject(value) || !isNullableString(value.message)) return false
  if (value.status === 'generated') return isRemediationRecord(value.remediation)
  return value.status === 'insufficient_context' && value.remediation === null
}

const isAssessmentResultSnapshot = (value: unknown) => isObject(value)
  && isNonEmptyString(value.analysis_id)
  && isNonEmptyString(value.assessment_title)
  && isNonEmptyString(value.filename)
  && isCount(value.answered_students)
  && isCount(value.correct_students)
  && isCount(value.affected_students)
  && isFiniteNumber(value.misconception_prevalence_percent)

const isResultsTrace = (value: unknown) => isObject(value)
  && isNonEmptyString(value.baseline_assessment_id)
  && isNonEmptyString(value.follow_up_assessment_id)
  && isNonEmptyString(value.baseline_analysis_id)
  && isNonEmptyString(value.follow_up_analysis_id)
  && isNonEmptyString(value.baseline_group_id)
  && isArrayOf(value.baseline_source_group_ids, isNonEmptyString) && value.baseline_source_group_ids.length > 0
  && (value.follow_up_group_id === null || isNonEmptyString(value.follow_up_group_id))
  && isNonEmptyString(value.remediation_id)
  && value.remediation_status === 'approved'
  && value.comparison_method === 'same_question_member_overlap_v1'

const isComparisonMetrics = (value: unknown) => isObject(value)
  && isAssessmentResultSnapshot(value.before)
  && isAssessmentResultSnapshot(value.after)
  && isCount(value.matched_answered_students)
  && isCount(value.missing_follow_up_students)
  && isFiniteNumber(value.percentage_point_reduction)
  && isFiniteNumber(value.correct_percentage_point_change)
  && isObject(value.transitions)
  && isCount(value.transitions.baseline_affected_students)
  && isCount(value.transitions.resolved_correct)
  && isCount(value.transitions.changed_but_still_incorrect)
  && isCount(value.transitions.still_struggling)
  && isCount(value.transitions.missing_from_baseline_group)
  && isCount(value.transitions.new_affected_students)

export const isFollowUpComparison = (value: unknown): value is FollowUpComparisonRecord => {
  if (!isObject(value)) return false
  const validPayload = value.status === 'completed'
    ? isResultsTrace(value.trace) && isComparisonMetrics(value.metrics)
    : value.status === 'insufficient_data' && (value.trace === null || isResultsTrace(value.trace)) && value.metrics === null
  return validPayload
    && isNonEmptyString(value.comparison_id)
    && (value.data_label === 'teacher_upload' || value.data_label === 'synthetic_demo')
    && isNonEmptyString(value.subject)
    && isNonEmptyString(value.grade_level)
    && isNonEmptyString(value.topic)
    && isNonEmptyString(value.question_id)
    && isNonEmptyString(value.question)
    && isNonEmptyString(value.misconception_label)
    && isNullableString(value.message)
    && isDateTime(value.created_at)
}
