import { expect, test, type Page, type Route } from '@playwright/test'

const assessment = { title: 'Review check', subject: 'Science', grade_level: '7', topic: 'Plants' }
const representatives = (student: string, answer: string) => [{ student_id: student, answer, similarity_to_medoid: 0.9 }]
const detected = [
  { group_id: 'grp_light', provisional_label: 'Pattern 1', interpretation_status: 'completed', question_id: 'Q1', question: 'How do plants make food?', correct_answer: 'Plants make glucose.', support_count: 3, eligible_response_count: 8, member_student_ids: ['S1', 'S2', 'S3'], representative_responses: representatives('S1', 'Plants eat light.'), coherence: 0.9 },
  { group_id: 'grp_soil', provisional_label: 'Pattern 2', interpretation_status: 'fallback', question_id: 'Q1', question: 'How do plants make food?', correct_answer: 'Plants make glucose.', support_count: 2, eligible_response_count: 8, member_student_ids: ['S4', 'S5'], representative_responses: representatives('S4', 'Food comes from soil.'), coherence: 0.82 },
]
const analysis = {
  assessment_id: 'assessment_review', analysis_id: 'analysis_review', status: 'completed', data_label: 'teacher_upload',
  filename: 'review.csv', assessment,
  summary: { response_count: 8, answered_count: 8, blank_count: 0, correct_count: 0, eligible_incorrect_count: 8, grouped_response_count: 5, outlier_count: 3, question_count: 1, group_count: 2 },
  embedding: { model_id: 'test/embedding', dimension: 3, preprocessing: 'answer_only_v1' },
  grouping: { algorithm: 'complete_link_cosine_v1', similarity_threshold: 0.7, minimum_support: 2 },
  groups: detected, message: null,
}
const reviewed = detected.map((group) => ({
  reviewed_group_id: group.group_id, display_label: group.provisional_label, status: 'active',
  source_group_ids: [group.group_id], question_id: group.question_id, question: group.question,
  correct_answer: group.correct_answer, support_count: group.support_count,
  eligible_response_count: group.eligible_response_count, member_student_ids: group.member_student_ids,
  representative_responses: group.representative_responses, coherence: group.coherence,
}))

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

async function installApi(page: Page, options: { lockedGroupIds?: string[] } = {}) {
  let active = structuredClone(reviewed)
  let dismissed: typeof active = []
  const events: unknown[] = []
  let reviewGets = 0
  let reviewFailuresRemaining = 0

  await page.route('http://api.classlens.test/**', async (route) => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname
    if (pathname === '/health') return json(route, { status: 'ok', service: 'classlens-api' })
    if (pathname === `/api/v1/assessments/analyses/${analysis.analysis_id}`) return json(route, analysis)
    if (pathname === `/api/v1/assessments/analyses/${analysis.analysis_id}/group-reviews`) {
      if (request.method() === 'GET') {
        reviewGets += 1
        if (reviewFailuresRemaining > 0) {
          reviewFailuresRemaining -= 1
          return json(route, { error: { code: 'review_unavailable', message: 'Review state unavailable.', retryable: true } }, 503)
        }
        return json(route, { analysis_id: analysis.analysis_id, revision: events.length, active_groups: active, dismissed_groups: dismissed, locked_group_ids: options.lockedGroupIds ?? [], events })
      }
      const body = request.postDataJSON()
      if (body.label === 'Conflict label') return json(route, { error: { code: 'group_review_stale', message: 'Another review changed this evidence.', retryable: false } }, 409)
      const previous = { analysis_id: analysis.analysis_id, revision: events.length, groups: [...active, ...dismissed] }
      let resultingId = body.group_ids[0]
      if (body.action === 'rename') active.find((group) => group.reviewed_group_id === resultingId)!.display_label = body.label
      if (body.action === 'merge') {
        const selected = active.filter((group) => body.group_ids.includes(group.reviewed_group_id))
        resultingId = 'rgrp_merged'
        active = [
          ...active.filter((group) => !body.group_ids.includes(group.reviewed_group_id)),
          { ...selected[0], reviewed_group_id: resultingId, display_label: body.label, source_group_ids: selected.flatMap((group) => group.source_group_ids), support_count: 5, member_student_ids: selected.flatMap((group) => group.member_student_ids), representative_responses: selected.flatMap((group) => group.representative_responses), coherence: null },
        ]
      }
      if (body.action === 'dismiss') {
        const target = active.find((group) => group.reviewed_group_id === resultingId)!
        active = active.filter((group) => group !== target); target.status = 'dismissed'; dismissed.push(target)
      }
      if (body.action === 'restore') {
        const target = dismissed.find((group) => group.reviewed_group_id === resultingId)!
        dismissed = dismissed.filter((group) => group !== target); target.status = 'active'; active.push(target)
      }
      const next = { analysis_id: analysis.analysis_id, revision: events.length + 1, groups: [...active, ...dismissed] }
      events.push({ event_id: `grev_${events.length + 1}`, analysis_id: analysis.analysis_id, sequence: events.length + 1, action: body.action, source_group_ids: body.group_ids, resulting_reviewed_group_id: resultingId, previous_state: events.length ? previous : null, next_state: next, review_note: body.review_note ?? null, created_at: `2026-10-14T00:00:0${events.length + 1}Z` })
      return json(route, { analysis_id: analysis.analysis_id, revision: events.length, active_groups: active, dismissed_groups: dismissed, locked_group_ids: options.lockedGroupIds ?? [], events })
    }
    return json(route, { error: { code: 'unexpected', message: `${request.method()} ${pathname}` } }, 500)
  })
  return { failNextReviewMount: () => { reviewFailuresRemaining = 2 }, getReviewCount: () => reviewGets }
}

test('teacher renames, merges, dismisses, restores, and sees ordered history', async ({ page }) => {
  await installApi(page)
  await page.addInitScript((analysisId) => localStorage.setItem('classlens.workflow.v1', JSON.stringify({ analysis_id: analysisId })), analysis.analysis_id)
  await page.goto('/analysis')
  await expect(page.getByText('AI-drafted label · teacher review needed')).toBeVisible()
  await expect(page.getByText('Detected pattern · AI label unavailable')).toBeVisible()

  await page.getByRole('button', { name: 'Review groups' }).click()
  await page.getByRole('button', { name: 'Rename Pattern 1' }).click()
  await page.getByLabel('New label').fill('Light is energy, not food')
  await page.getByRole('button', { name: 'Save label' }).click()
  await expect(page.getByRole('button', { name: /^Teacher-reviewed label.*Light is energy, not food/ })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('button', { name: /^Teacher-reviewed label.*Light is energy, not food/ })).toBeVisible()

  await page.getByRole('button', { name: 'Review groups' }).click()
  await page.getByLabel('Select Light is energy, not food').check()
  await page.getByLabel('Select Pattern 2').check()
  await page.getByLabel('Merged label').fill('Sources of plant food')
  await page.getByRole('button', { name: 'Merge 2 groups' }).click()
  await expect(page.getByText('5 affected responses in the merged group')).toBeVisible()
  await page.getByRole('button', { name: 'Confirm merge' }).click()
  await expect(page.getByText('Coherence not recalculated')).toBeVisible()
  await expect(page.getByRole('button', { name: /^Teacher-reviewed label.*Sources of plant food/ })).toBeVisible()

  await page.getByRole('button', { name: 'Dismiss Sources of plant food' }).click()
  await page.getByRole('button', { name: 'Confirm dismiss' }).click()
  await page.getByText('Dismissed (1)').click()
  await page.getByRole('button', { name: 'Restore Sources of plant food' }).click()
  await expect(page.getByText('4 review actions')).toBeVisible()
})

test('a controlled conflict preserves visible review state and explains recovery', async ({ page }) => {
  await installApi(page)
  await page.addInitScript((analysisId) => localStorage.setItem('classlens.workflow.v1', JSON.stringify({ analysis_id: analysisId })), analysis.analysis_id)
  await page.goto('/analysis')
  await page.getByRole('button', { name: 'Review groups' }).click()
  await page.getByRole('button', { name: 'Rename Pattern 1' }).click()
  await page.getByLabel('New label').fill('Conflict label')
  await page.getByRole('button', { name: 'Save label' }).click()
  await expect(page.getByText('Another review changed this evidence.')).toBeVisible()
  await expect(page.getByRole('button', { name: /^AI-drafted label .*Pattern 1/ })).toBeVisible()
})

test('review locks only affected groups and restored review fetch can be retried', async ({ page }) => {
  const api = await installApi(page, { lockedGroupIds: ['grp_light'] })
  await page.addInitScript((analysisId) => localStorage.setItem('classlens.workflow.v1', JSON.stringify({ analysis_id: analysisId })), analysis.analysis_id)
  await page.goto('/analysis')
  await expect(page.getByRole('region', { name: 'Teacher group review' })).toBeVisible()
  await page.getByRole('button', { name: '01 Dashboard' }).click()
  api.failNextReviewMount()
  await page.getByRole('button', { name: '03 Learning gaps' }).click()
  await expect(page.getByText('Review state unavailable.')).toBeVisible()
  await page.getByRole('button', { name: 'Try again' }).click()
  await page.getByRole('button', { name: 'Review groups' }).click()
  await expect(page.getByRole('button', { name: 'Rename Pattern 1' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Rename Pattern 2' })).toBeEnabled()
})
