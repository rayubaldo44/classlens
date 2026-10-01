# Demo Guide

**Implementation status:** Planned. No demo dataset, teacher material, seeded database, or ClassLens UI flow exists in the repository as of 2026-10-01.

This document defines the reproducible hackathon demonstration. It must remain honest about synthetic, seeded, cached, or live-generated content.

## Scenario

- **Subject:** Grade 7 Science
- **Topic:** Photosynthesis
- **Class size:** approximately 40–50 synthetic students
- **Teacher goal:** understand why several students missed a free-response question, then prepare a grounded intervention and inspect follow-up performance.

Core example pattern:

- “Plants eat sunlight.”
- “Sunlight is the food of plants.”
- “Plants consume sunlight to grow.”

These responses may indicate a recurring misunderstanding of sunlight as food rather than an energy source used to produce glucose during photosynthesis. The demo must present this as a potential misconception supported by responses and reviewed by the teacher, not as a certain diagnosis of student thinking.

## Reproducible dataset requirements

Create these fixtures during implementation; do not hand-edit production data before the demo:

1. **Assessment definition** with stable question IDs, exact prompts, learning objectives, expected answers/rubrics, subject, grade, and topic.
2. **Baseline response CSV** with 40–50 stable synthetic student IDs, valid quoting, several questions if time permits, correctness according to the chosen transparent scoring contract, and a deliberate mix of:
   - correct explanations;
   - the sunlight-as-food paraphrases;
   - other coherent errors that should remain separate;
   - unique/outlier errors;
   - at least one blank response;
   - no real student names or personal data.
3. **Teacher-provided learning material** that accurately explains sunlight as an energy source and glucose as a product/storage form, with a known passage locator.
4. **Expected analysis manifest** listing intended row counts, eligibility counts, known pattern members, acceptable outliers, and expected retrieved passage IDs. This supports automated verification without forcing every algorithm result.
5. **Follow-up response CSV** using the same synthetic student/question IDs, with missing records represented by absence and the file clearly labeled `demo_seed` if outcomes are predetermined.
6. **Reset/seed command or documented procedure** that restores the same clean state before each run.

Fix seeds wherever the selected grouping or fixture-generation code uses randomness. Record model IDs and thresholds. Do not claim the dataset exists until these files are committed and verified.

## Golden-path click sequence

1. Open the teacher dashboard and choose **Load photosynthesis demo** or upload the assessment and baseline CSV.
2. Review the validation preview: class size, question count, valid/blank/incorrect counts, and synthetic-data label.
3. Start analysis and show visible progress rather than a frozen screen.
4. Open the resulting group **Sunlight treated as plant food** (final title may vary after evaluation).
5. Point to group support, the question/expected concept, and exact representative responses.
6. Select or upload the prepared teacher lesson material.
7. Show the retrieved passage with filename and page/section before generation.
8. Generate the activity and follow-up questions; show their passage references.
9. Make a small teacher edit and approve the intervention.
10. Load clearly labeled synthetic follow-up results.
11. Show baseline and follow-up counts/percentages plus missing-data and non-causality notes.

Every screen in the sequence needs a deterministic navigation path back to the next step. Avoid dead-end demo controls.

## Approximately three-minute pitch

### 0:00–0:30 — Problem and promise

“Grades show me which students missed the question. They do not show that twelve students may share the same underlying idea in different words. ClassLens helps a teacher find that pattern and decide what to do next.”

Load the synthetic photosynthesis class and point out validation and class counts.

### 0:30–1:15 — Detect and verify

Run or open the completed analysis. Select the sunlight-as-food group. Show the three example paraphrases, support count, expected concept, and caution that this is a potential misconception for teacher review.

Explain the division of responsibility: embeddings surface the pattern; the LLM communicates it; the teacher judges it.

### 1:15–2:15 — Ground and approve

Choose the teacher lesson material. Show the exact retrieved passage about sunlight energy and glucose. Generate remediation, point to source references, make a quick edit, and approve it.

Explain that retrieval grounds the intervention in teacher-provided content; it did not create the original misconception group.

### 2:15–2:50 — Measure

Load the clearly labeled synthetic follow-up. Show transparent before/after counts and missing results. State that the comparison demonstrates workflow and observed change, not causal proof.

### 2:50–3:00 — Close

“Grades tell teachers who is struggling. ClassLens helps explain why—and keeps the teacher in control of what happens next.”

## What must work live

- The frontend and backend load at the deployed or local demo URLs.
- The prepared assessment/CSV passes real validation.
- Analysis returns stored response evidence and a coherent target group.
- The detail view shows exact fixture responses rather than invented examples.
- The prepared material is actually extracted/indexed or loaded from a clearly identified preprocessed fixture.
- Retrieval displays an exact relevant passage and source locator.
- Remediation is tied to that passage and can be edited and approved.
- Follow-up data is labeled and the arithmetic is correct.
- Expected error states have readable UI, even if only the happy path is shown on stage.

## Backup strategy

Reliability is the priority, so prepare fallbacks before the event:

1. Keep local copies of the exact synthetic assessment, CSVs, and teacher material.
2. Keep a deterministic seeded analysis result derived from those same fixtures, including exact membership and provenance.
3. If live AI is unavailable, switch through an explicit **Seeded demo result** control or configuration and say that the model output was precomputed from the displayed data.
4. If document extraction is unreliable on the venue network, use a pre-extracted chunk fixture from the same visible document and label it as preprocessed.
5. Keep screenshots or a short recording only as the final presentation fallback, labeled as a recorded run.

Never present seeded groups, retrieval, remediation, or follow-up results as live provider output. Never silently replace a failure with fabricated content.

## Pre-demo checklist

### Data and expected outputs

- [ ] Synthetic assessment, baseline CSV, material, manifest, and follow-up CSV exist and are versioned.
- [ ] Row counts, blank counts, scoring, group membership, and result arithmetic match the manifest.
- [ ] No real student data appears in files, logs, screenshots, or browser storage.
- [ ] Seeded/precomputed items are labeled in fixtures and UI.

### Services and configuration

- [ ] Frontend, backend, and database URLs are correct for the demo environment.
- [ ] Required secrets are present server-side and absent from the frontend bundle.
- [ ] CORS and HTTPS work from the presentation machine/network.
- [ ] Provider quotas, model availability, and timeouts were checked.
- [ ] Health checks and logs are accessible without exposing sensitive data.

### Golden path

- [ ] Run the full click sequence from a clean reset twice.
- [ ] Confirm CSV validation and preview counts.
- [ ] Confirm the target group and exact evidence.
- [ ] Confirm the expected source passage and locator.
- [ ] Confirm remediation references only available passages.
- [ ] Confirm edit, approve, and reject states persist correctly.
- [ ] Confirm follow-up missing values and percentages render correctly.

### Presentation

- [ ] Browser zoom, resolution, and text size are readable on the projector.
- [ ] Demo tabs/files are prearranged and notifications are muted.
- [ ] The three-minute script is rehearsed with a timer.
- [ ] Local fixtures, seeded-mode instructions, screenshots, and recording are immediately accessible.
- [ ] The presenter knows the one-sentence explanation for live, seeded, and preprocessed data.
