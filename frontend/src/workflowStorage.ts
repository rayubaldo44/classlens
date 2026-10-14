export type WorkflowPointer = {
  analysis_id?: string
  group_id?: string
  material_id?: string
  remediation_id?: string
  comparison_id?: string
}

type WorkflowIssue = { code: 'invalid_saved_workflow' | 'incomplete_saved_workflow'; message: string }
type WorkflowReadResult = { pointer: WorkflowPointer | null; issue: WorkflowIssue | null }

const pointerKeys = ['analysis_id', 'group_id', 'material_id', 'remediation_id', 'comparison_id'] as const
const isObject = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)
const isIdentifier = (value: unknown): value is string => typeof value === 'string' && value.length > 0

export const parseWorkflowPointer = (raw: string | null): WorkflowReadResult => {
  if (raw === null) return { pointer: {}, issue: null }
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return {
      pointer: null,
      issue: { code: 'invalid_saved_workflow', message: 'The saved workflow reference is damaged. Start a new workflow to replace it.' },
    }
  }
  if (!isObject(parsed)
    || Object.keys(parsed).some((key) => !pointerKeys.includes(key as typeof pointerKeys[number]))
    || pointerKeys.some((key) => parsed[key] !== undefined && !isIdentifier(parsed[key]))) {
    return {
      pointer: null,
      issue: { code: 'invalid_saved_workflow', message: 'The saved workflow reference has invalid identifiers. Start a new workflow to replace it.' },
    }
  }

  const pointer = Object.fromEntries(
    pointerKeys.filter((key) => parsed[key] !== undefined).map((key) => [key, parsed[key]]),
  ) as WorkflowPointer
  const isIncomplete = Boolean(
    (pointer.group_id && !pointer.analysis_id)
    || (pointer.material_id && !pointer.group_id)
    || (pointer.remediation_id && !pointer.material_id)
    || (pointer.comparison_id && !pointer.remediation_id),
  )
  if (isIncomplete) {
    return {
      pointer: null,
      issue: { code: 'incomplete_saved_workflow', message: 'The saved workflow is missing an earlier step. Start a new workflow to rebuild the evidence chain.' },
    }
  }
  return { pointer, issue: null }
}

export const retrievalMatchesWorkflow = (pointer: WorkflowPointer, retrieval: unknown): boolean => isObject(retrieval)
  && isObject(retrieval.material)
  && retrieval.group_id === pointer.group_id
  && retrieval.material.material_id === pointer.material_id

export const analysisMatchesWorkflow = (pointer: WorkflowPointer, analysis: unknown): boolean => isObject(analysis)
  && analysis.analysis_id === pointer.analysis_id

export const groupReviewMatchesWorkflow = (pointer: WorkflowPointer, reviews: unknown): boolean => isObject(reviews)
  && reviews.analysis_id === pointer.analysis_id
  && Array.isArray(reviews.active_groups)
  && (!pointer.group_id || reviews.active_groups.some(
    (group) => isObject(group) && group.reviewed_group_id === pointer.group_id,
  ))

export const remediationMatchesWorkflow = (pointer: WorkflowPointer, remediation: unknown): boolean => isObject(remediation)
  && remediation.remediation_id === pointer.remediation_id
  && remediation.analysis_id === pointer.analysis_id
  && remediation.group_id === pointer.group_id

export const comparisonMatchesWorkflow = (pointer: WorkflowPointer, comparison: unknown): boolean => isObject(comparison)
  && comparison.comparison_id === pointer.comparison_id
  && isObject(comparison.trace)
  && comparison.trace.baseline_analysis_id === pointer.analysis_id
  && comparison.trace.baseline_group_id === pointer.group_id
  && comparison.trace.remediation_id === pointer.remediation_id
