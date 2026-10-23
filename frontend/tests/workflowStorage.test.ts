import assert from 'node:assert/strict'
import test from 'node:test'

import {
  analysisMatchesWorkflow,
  comparisonMatchesWorkflow,
  parseWorkflowPointer,
  remediationMatchesWorkflow,
  retrievalMatchesWorkflow,
  groupReviewMatchesWorkflow,
} from '../src/workflowStorage.ts'

test('saved workflow parser accepts a complete ordered pointer chain', () => {
  const result = parseWorkflowPointer(JSON.stringify({
    analysis_id: 'analysis_demo', group_id: 'grp_demo', material_id: 'mat_demo',
    remediation_id: 'rem_demo', comparison_id: 'comparison_demo',
  }))

  assert.deepEqual(result, {
    pointer: {
      analysis_id: 'analysis_demo', group_id: 'grp_demo', material_id: 'mat_demo',
      remediation_id: 'rem_demo', comparison_id: 'comparison_demo',
    },
    issue: null,
  })
})

test('saved workflow parser rejects invalid JSON and non-string identifiers', () => {
  assert.equal(parseWorkflowPointer('{broken').pointer, null)
  assert.equal(parseWorkflowPointer('{broken').issue?.code, 'invalid_saved_workflow')
  assert.equal(parseWorkflowPointer(JSON.stringify({ analysis_id: 42 })).pointer, null)
  assert.equal(parseWorkflowPointer(JSON.stringify({ analysis_id: 42 })).issue?.code, 'invalid_saved_workflow')
})

test('saved workflow parser rejects pointers that skip required upstream identifiers', () => {
  const result = parseWorkflowPointer(JSON.stringify({ analysis_id: 'analysis_demo', remediation_id: 'rem_demo' }))

  assert.equal(result.pointer, null)
  assert.equal(result.issue?.code, 'incomplete_saved_workflow')
})

test('restored records must match every saved upstream identifier', () => {
  const pointer = {
    analysis_id: 'analysis_demo', group_id: 'grp_demo', material_id: 'mat_demo',
    remediation_id: 'rem_demo', comparison_id: 'comparison_demo',
  }

  assert.equal(analysisMatchesWorkflow(pointer, { analysis_id: 'analysis_demo', groups: [{ group_id: 'grp_demo' }] }), true)
  assert.equal(analysisMatchesWorkflow(pointer, { analysis_id: 'analysis_demo', groups: [{ group_id: 'grp_other' }] }), true)
  assert.equal(retrievalMatchesWorkflow(pointer, { group_id: 'grp_demo', material: { material_id: 'mat_other' } }), false)
  assert.equal(remediationMatchesWorkflow(pointer, { remediation_id: 'rem_demo', analysis_id: 'analysis_demo', group_id: 'grp_other' }), false)
  assert.equal(comparisonMatchesWorkflow(pointer, {
    comparison_id: 'comparison_demo',
    trace: { baseline_analysis_id: 'analysis_demo', baseline_group_id: 'grp_demo', remediation_id: 'rem_other' },
  }), false)
})

test('reviewed selection recovery accepts only an active reviewed group', () => {
  const pointer = { analysis_id: 'analysis_demo', group_id: 'rgrp_merged' }
  const reviews = {
    analysis_id: 'analysis_demo',
    active_groups: [{ reviewed_group_id: 'rgrp_merged' }],
    dismissed_groups: [{ reviewed_group_id: 'grp_dismissed' }],
  }
  assert.equal(groupReviewMatchesWorkflow(pointer, reviews), true)
  assert.equal(groupReviewMatchesWorkflow({ ...pointer, group_id: 'grp_dismissed' }, reviews), false)
  assert.equal(groupReviewMatchesWorkflow({ ...pointer, group_id: 'rgrp_stale' }, reviews), false)
})
