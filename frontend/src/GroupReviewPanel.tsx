import { useState, type FormEvent } from 'react'
import { ApiError, applyGroupReview, type GroupReviewActionRequest, type GroupReviewResponse, type ReviewedMisconceptionGroup } from './api/client'

type Pending = { action: 'dismiss'; group: ReviewedMisconceptionGroup } | { action: 'merge'; groups: ReviewedMisconceptionGroup[]; label: string } | null

export function GroupReviewPanel({ reviews, onChange }: { reviews: GroupReviewResponse; onChange: (value: GroupReviewResponse) => void }) {
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [renaming, setRenaming] = useState<ReviewedMisconceptionGroup | null>(null)
  const [renameLabel, setRenameLabel] = useState('')
  const [mergeLabel, setMergeLabel] = useState('')
  const [dismissNote, setDismissNote] = useState('')
  const [pending, setPending] = useState<Pending>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const selectedGroups = reviews.active_groups.filter((group) => selected.includes(group.reviewed_group_id))
  const selectedSupport = new Set(selectedGroups.flatMap((group) => group.member_student_ids)).size
  const isLocked = (group: ReviewedMisconceptionGroup) => reviews.locked_group_ids.includes(group.reviewed_group_id)
  const selectedLocked = selectedGroups.some(isLocked)

  const submit = async (request: GroupReviewActionRequest) => {
    setBusy(true); setError('')
    try {
      onChange(await applyGroupReview(reviews.analysis_id, request))
      setSelected([]); setRenaming(null); setPending(null); setMergeLabel(''); setDismissNote('')
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught.message : 'The review action could not be saved. Reload and try again.')
    } finally { setBusy(false) }
  }
  const saveRename = (event: FormEvent) => {
    event.preventDefault()
    if (renaming && renameLabel.trim()) void submit({ action: 'rename', group_ids: [renaming.reviewed_group_id], label: renameLabel, expected_revision: reviews.revision })
  }

  return <section className="group-review" aria-labelledby="group-review-title"><div className="group-review__heading"><div><h2 id="group-review-title">Teacher group review</h2><p>Adjust labels and groupings without changing the detected analysis.</p></div><button className="button secondary" type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}>{open ? 'Close review' : 'Review groups'}</button></div>
    {reviews.locked_group_ids.length > 0 && <p className="review-lock" role="status">Groups used by a remediation are locked; unrelated evidence remains reviewable.</p>}{error && <p className="review-error" role="alert">{error}</p>}
    {open && <div className="group-review__body"><div className="review-group-list">{reviews.active_groups.map((group) => <article className="review-group-row" key={group.reviewed_group_id}><label className="review-select"><input type="checkbox" checked={selected.includes(group.reviewed_group_id)} disabled={isLocked(group) || busy} aria-label={`Select ${group.display_label}`} onChange={(event) => setSelected((current) => event.target.checked ? [...current, group.reviewed_group_id] : current.filter((id) => id !== group.reviewed_group_id))} /><span><strong>{group.display_label}</strong><small>{group.support_count} of {group.eligible_response_count} affected</small></span></label><div className="review-row-actions"><button type="button" className="text-button" disabled={isLocked(group) || busy} aria-label={`Rename ${group.display_label}`} onClick={() => { setRenaming(group); setRenameLabel(group.display_label); setPending(null) }}>Rename</button><button type="button" className="text-button danger" disabled={isLocked(group) || busy} aria-label={`Dismiss ${group.display_label}`} onClick={() => { setPending({ action: 'dismiss', group }); setRenaming(null) }}>Dismiss</button></div>{group.source_group_ids.length > 1 && <p className="review-provenance">Sources: {group.source_group_ids.join(', ')} · Coherence not recalculated</p>}</article>)}</div>
      {renaming && <form className="review-inline-form" onSubmit={saveRename}><label htmlFor="review-rename-label">New label</label><input id="review-rename-label" value={renameLabel} maxLength={120} autoFocus onChange={(event) => setRenameLabel(event.target.value)} /><div className="review-form-actions"><button className="button primary" disabled={busy || !renameLabel.trim()}>Save label</button><button className="button secondary" type="button" onClick={() => setRenaming(null)}>Cancel</button></div></form>}
      <div className="review-merge"><label htmlFor="review-merge-label">Merged label</label><input id="review-merge-label" value={mergeLabel} maxLength={120} disabled={busy} onChange={(event) => setMergeLabel(event.target.value)} /><button className="button secondary" type="button" disabled={busy || selectedLocked || selectedGroups.length < 2 || !mergeLabel.trim()} onClick={() => setPending({ action: 'merge', groups: selectedGroups, label: mergeLabel })}>Merge {selectedGroups.length} groups</button></div>
      {pending?.action === 'merge' && <div className="review-confirm" role="group" aria-label="Confirm group merge"><strong>{selectedSupport} affected responses in the merged group</strong><p>This combines exact member evidence from {pending.groups.length} groups. Coherence will not be recalculated.</p><div className="review-form-actions"><button className="button primary" disabled={busy} onClick={() => void submit({ action: 'merge', group_ids: pending.groups.map((group) => group.reviewed_group_id), label: pending.label, expected_revision: reviews.revision })}>Confirm merge</button><button className="button secondary" onClick={() => setPending(null)}>Cancel</button></div></div>}
      {pending?.action === 'dismiss' && <div className="review-confirm" role="group" aria-label="Confirm group dismissal"><strong>Dismiss {pending.group.display_label}?</strong><p>It will leave the actionable list but remain available to restore.</p><label htmlFor="review-dismiss-note">Optional note</label><textarea id="review-dismiss-note" rows={2} value={dismissNote} onChange={(event) => setDismissNote(event.target.value)} /><div className="review-form-actions"><button className="button primary" disabled={busy} onClick={() => void submit({ action: 'dismiss', group_ids: [pending.group.reviewed_group_id], review_note: dismissNote || undefined, expected_revision: reviews.revision })}>Confirm dismiss</button><button className="button secondary" onClick={() => setPending(null)}>Cancel</button></div></div>}
      <details className="review-disclosure"><summary>Dismissed ({reviews.dismissed_groups.length})</summary>{reviews.dismissed_groups.length === 0 ? <p>No dismissed groups.</p> : reviews.dismissed_groups.map((group) => <div className="dismissed-row" key={group.reviewed_group_id}><span><strong>{group.display_label}</strong><small>{group.support_count} affected responses</small></span><button className="text-button" disabled={isLocked(group) || busy} aria-label={`Restore ${group.display_label}`} onClick={() => void submit({ action: 'restore', group_ids: [group.reviewed_group_id], expected_revision: reviews.revision })}>Restore</button></div>)}</details>
      <details className="review-disclosure"><summary>{reviews.events.length} review actions</summary><ol className="review-history">{reviews.events.map((event) => <li key={event.event_id}><strong>{event.action}</strong><span>{event.source_group_ids.join(', ')}</span><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></li>)}</ol></details>
    </div>}
  </section>
}
