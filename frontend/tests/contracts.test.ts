import assert from 'node:assert/strict'
import test from 'node:test'

import {
  isAnalysisResponse,
  isAssessmentPreview,
  isFollowUpComparison,
  isMaterialIngestionResponse,
  isMaterialRetrievalResponse,
  isRemediationGenerationResponse,
  isRemediationRecord,
  isGroupReviewResponse,
} from '../src/api/contracts.ts'

const representative = { student_id: 'S001', answer: 'Plants eat sunlight.', similarity_to_medoid: 0.96 }
const group = {
  group_id: 'grp_demo', provisional_label: 'Potential misconception pattern 1', interpretation_status: 'not_requested',
  question_id: 'Q1', question: 'How do plants make food?', correct_answer: 'Plants make glucose.',
  support_count: 3, eligible_response_count: 8, member_student_ids: ['S001', 'S002', 'S003'],
  representative_responses: [representative], coherence: 0.91,
}
const assessment = { title: 'Demo', subject: 'Science', grade_level: '7', topic: 'Photosynthesis' }
const analysis = {
  assessment_id: 'assessment_demo', analysis_id: 'analysis_demo', status: 'completed', data_label: 'synthetic_demo',
  filename: 'responses.csv', assessment,
  summary: { response_count: 10, answered_count: 9, blank_count: 1, correct_count: 1, eligible_incorrect_count: 8, grouped_response_count: 3, outlier_count: 5, question_count: 1, group_count: 1 },
  embedding: { model_id: 'embedding-model', dimension: 384, preprocessing: 'answer_only_v1' },
  grouping: { algorithm: 'complete_link_cosine_v1', similarity_threshold: 0.7, minimum_support: 3 },
  groups: [group], message: null,
}
const material = {
  material_id: 'mat_demo', title: 'Lesson notes', filename: 'lesson.txt', source_kind: 'synthetic_demo',
  content_hash: 'hash', chunk_count: 1, chunk_size_chars: 900, chunk_overlap_chars: 120,
  embedding_model: 'embedding-model', embedding_dimension: 384,
}
const retrieval = {
  status: 'retrieved', group_id: 'grp_demo', source_group_ids: ['grp_demo'], material,
  retrieval: { algorithm: 'cosine_similarity_v1', top_k: 3, minimum_relevance_score: 0.42, embedding_model: 'embedding-model' },
  results: [{ chunk_id: 'chunk_001', chunk_index: 0, text: 'Plants use light energy.', similarity: 0.83, start_char: 0, end_char: 24 }],
  message: null,
}
const content = {
  misconception_summary: 'Students treat sunlight as food.', learning_objective: 'Separate energy and matter.',
  teacher_explanation: 'Light supplies energy.', corrected_concept: 'Plants make glucose.', activity: 'Sort cards.',
  analogy: null, follow_up_questions: [{ prompt: 'What does light provide?', expected_answer: 'Energy.' }],
  source_references: ['chunk_001'],
}
const remediation = {
  remediation_id: 'rem_demo', status: 'approved', analysis_id: 'analysis_demo', group_id: 'grp_demo', source_group_ids: ['grp_demo'],
  provider: 'google-gemini', model: 'gemini-test', prompt_version: 'grounded_remediation_v1',
  generated_content: content, content,
  sources: [{ material_id: 'mat_demo', material_title: 'Lesson notes', filename: 'lesson.txt', chunk_id: 'chunk_001', chunk_index: 0, text: 'Plants use light energy.', similarity: 0.83, start_char: 0, end_char: 24 }],
  review_notes: null, created_at: '2026-10-13T00:00:00Z', updated_at: '2026-10-13T00:00:00Z',
}
const snapshot = {
  analysis_id: 'analysis_demo', assessment_title: 'Demo', filename: 'responses.csv', answered_students: 9,
  correct_students: 1, affected_students: 3, misconception_prevalence_percent: 33.3,
}
const comparison = {
  comparison_id: 'comparison_demo', status: 'completed', data_label: 'synthetic_demo', subject: 'Science',
  grade_level: '7', topic: 'Photosynthesis', question_id: 'Q1', question: 'How do plants make food?',
  misconception_label: 'Potential misconception pattern 1',
  trace: { baseline_assessment_id: 'assessment_demo', follow_up_assessment_id: 'assessment_followup', baseline_analysis_id: 'analysis_demo', follow_up_analysis_id: 'analysis_followup', baseline_group_id: 'grp_demo', baseline_source_group_ids: ['grp_demo'], follow_up_group_id: 'grp_followup', remediation_id: 'rem_demo', remediation_status: 'approved', comparison_method: 'same_question_member_overlap_v1' },
  metrics: { before: snapshot, after: { ...snapshot, analysis_id: 'analysis_followup' }, matched_answered_students: 8, missing_follow_up_students: 1, percentage_point_reduction: 20, correct_percentage_point_change: 30, transitions: { baseline_affected_students: 3, resolved_correct: 2, changed_but_still_incorrect: 0, still_struggling: 1, missing_from_baseline_group: 0, new_affected_students: 0 } },
  message: null, created_at: '2026-10-13T00:00:00Z',
}
const reviewedGroup = {
  reviewed_group_id: 'grp_demo', display_label: 'Teacher label', status: 'active', source_group_ids: ['grp_demo'],
  question_id: 'Q1', question: 'How do plants make food?', correct_answer: 'Plants make glucose.',
  support_count: 3, eligible_response_count: 8, member_student_ids: ['S001', 'S002', 'S003'],
  representative_responses: [representative], coherence: null,
}
const reviewState = {
  analysis_id: 'analysis_demo', revision: 1, active_groups: [reviewedGroup], dismissed_groups: [],
  locked_group_ids: [],
  events: [{
    event_id: 'grev_1', analysis_id: 'analysis_demo', sequence: 1, action: 'merge',
    source_group_ids: ['grp_demo'], resulting_reviewed_group_id: 'grp_demo', previous_state: null,
    next_state: { analysis_id: 'analysis_demo', revision: 1, groups: [reviewedGroup] },
    review_note: null, created_at: '2026-10-14T00:00:00Z',
  }],
}

test('assessment preview rejects malformed nested summary values', () => {
  const preview = {
    status: 'validated', data_label: 'synthetic_demo', filename: 'responses.csv', assessment,
    summary: { response_count: '10', answered_count: 9, blank_count: 1, student_count: 10, question_count: 1, correct_count: 1, incorrect_count: 8 },
    sample_responses: [],
  }
  assert.equal(isAssessmentPreview(preview), false)
})

test('analysis rejects malformed representative evidence', () => {
  assert.equal(isAnalysisResponse(analysis), true)
  const malformed = structuredClone(analysis)
  malformed.groups[0].representative_responses[0].answer = 42 as unknown as string
  assert.equal(isAnalysisResponse(malformed), false)
})

test('material responses reject malformed nested material and chunk fields', () => {
  assert.equal(isMaterialIngestionResponse({ status: 'ready', material, message: 'Ready.' }), true)
  assert.equal(isMaterialIngestionResponse({ status: 'ready', material: { ...material, chunk_count: '1' }, message: 'Ready.' }), false)
  assert.equal(isMaterialRetrievalResponse(retrieval), true)
  const malformed = structuredClone(retrieval)
  malformed.results[0].end_char = '24' as unknown as number
  assert.equal(isMaterialRetrievalResponse(malformed), false)
})

test('remediation responses reject missing nested generated content', () => {
  assert.equal(isRemediationRecord(remediation), true)
  const malformed = structuredClone(remediation) as Record<string, unknown>
  const malformedContent = structuredClone(content) as Record<string, unknown>
  malformedContent.follow_up_questions = [{ prompt: 'What does light provide?' }]
  malformed.generated_content = malformedContent
  assert.equal(isRemediationRecord(malformed), false)
  assert.equal(isRemediationGenerationResponse({ status: 'generated', remediation: null, message: null }), false)
})

test('completed comparison rejects malformed nested metrics', () => {
  assert.equal(isFollowUpComparison(comparison), true)
  const malformed = structuredClone(comparison)
  malformed.metrics.transitions.resolved_correct = '2' as unknown as number
  assert.equal(isFollowUpComparison(malformed), false)
})

test('group review accepts nullable coherence and rejects malformed provenance or history', () => {
  assert.equal(isGroupReviewResponse(reviewState), true)
  const malformedSource = structuredClone(reviewState)
  malformedSource.active_groups[0].source_group_ids = ['']
  assert.equal(isGroupReviewResponse(malformedSource), false)
  const malformedHistory = structuredClone(reviewState)
  malformedHistory.events[0].sequence = 2
  assert.equal(isGroupReviewResponse(malformedHistory), false)
})

test('group review requires per-group remediation lock state', () => {
  const missingLocks = structuredClone(reviewState) as Record<string, unknown>
  delete missingLocks.locked_group_ids
  assert.equal(isGroupReviewResponse(missingLocks), false)
  assert.equal(isGroupReviewResponse({ ...reviewState, locked_group_ids: ['grp_demo'] }), true)
})
