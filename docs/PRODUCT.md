# Product Requirements

This document is the authority for what ClassLens should do and the educational constraints it must respect. Current implementation state belongs in [STATUS.md](../STATUS.md); technical design belongs in the other documents under `docs/`.

## Vision

**ClassLens — From grades to understanding.**

Traditional gradebooks identify which students performed poorly but rarely help teachers see recurring reasons behind those results. Students can express the same underlying conceptual misunderstanding in very different words, making patterns difficult to find manually across a class.

ClassLens analyzes free-text student responses to propose recurring misconception groups, presents the evidence behind each proposal, retrieves relevant teacher-provided learning material, and drafts targeted remediation for teacher approval.

> Grades tell teachers who is struggling. ClassLens helps explain why.

The product principle is: **Embeddings detect the learning gap. RAG grounds the intervention. The LLM communicates the solution.** The teacher remains the final authority.

## Users

### Teachers

Teachers upload or load assessments and responses, review proposed misconceptions and evidence, supply instructional material, edit generated interventions, approve or reject them, and inspect follow-up results.

### Students

Students benefit from teacher-approved targeted remediation and follow-up assessment. A student-facing account or application is not required for the MVP.

## User stories

- As a teacher, I can load a valid response file and understand any validation problem before analysis begins.
- As a teacher, I can see proposed recurring misconceptions for a particular question rather than only low scores.
- As a teacher, I can inspect representative responses and group support before accepting an AI interpretation.
- As a teacher, I can rename, merge, dismiss, or restore proposed groups without losing their original evidence or review history.
- As a teacher, I can upload or select my own instructional material and see which passages support remediation.
- As a teacher, I can edit, approve, or reject a proposed intervention before it is used.
- As a teacher, I can compare transparent baseline and follow-up results and distinguish missing data from poor performance.
- As a student, I receive remediation aimed at the conceptual difficulty reflected in my work and reviewed by my teacher.

## Functional requirements

### Assessment intake

- Accept an assessment definition with question context, expected answer or rubric, and free-text student responses.
- Accept a CSV in the documented schema and validate file type, size, encoding, required columns, identifiers, and values.
- Show a normalized preview and counts before analysis.
- Preserve student text exactly for evidence; preprocessing used for models must not overwrite source responses.

### Analysis

- Identify eligible incorrect responses per question using an answer key, rubric, or explicit correctness field.
- Use embeddings to represent response meaning and propose recurring semantic groups within the same question.
- Permit outliers and an insufficient-data outcome; do not force every response into a group.
- **Planned after the current golden path:** use an LLM to draft concise, teacher-readable interpretations using only provided question context and group evidence. The implemented MVP uses generic provisional group labels.
- Record enough model, prompt, and analysis metadata to explain and reproduce the demo result.

### Evidence review

- Show group size, question, expected concept, representative responses, and relevant caveats.
- Keep response wording faithful to the submitted data.
- Let the teacher treat a group as a proposal rather than a proven diagnosis.
- Preserve detected groups as immutable evidence and store teacher review as a separate, revisioned overlay.
- Allow same-question groups to be renamed, merged, dismissed, or restored; merged groups must retain the complete source-group and member provenance and must not claim a recomputed coherence score.
- Show ordered review history, including optional teacher notes, and prevent affected group-review changes after remediation exists so downstream evidence remains stable.

### Learning-material retrieval

- Accept supported teacher-provided instructional material.
- Extract and chunk its text while retaining source location metadata when available.
- Retrieve passages relevant to the selected potential misconception.
- Show a clear no-relevant-material result when the best evidence does not meet the chosen threshold.

### Remediation and approval

- Generate a focused explanation or activity plus follow-up questions from the selected group evidence and retrieved passages.
- Associate generated claims and source references with the retrieved content.
- Allow the teacher to edit, approve, or reject the draft.
- Never deliver or mark an intervention approved without an explicit teacher action.

### Results

- Record or load follow-up results with stable identifiers.
- Compare baseline and follow-up using visible counts, denominators, and percentages.
- Clearly label synthetic, seeded, or precomputed demo data.
- Display missing follow-up results as unavailable.

## MVP golden path

1. Teacher uploads or loads an assessment and student-response CSV.
2. The backend validates and normalizes the input.
3. An embedding model converts relevant student responses into semantic vectors.
4. Similar incorrect responses are grouped into potential recurring misconceptions.
5. The current MVP assigns generic provisional labels and displays exact group evidence. LLM-authored group descriptions remain a proposed post-demo step.
6. The teacher reviews the proposals and may rename, merge, dismiss, or restore them while retaining exact source evidence and history.
7. The teacher opens an active reviewed group and sees representative responses and supporting evidence.
8. The teacher uploads or selects relevant instructional material.
9. Retrieval finds relevant passages from that material.
10. An LLM generates a targeted remediation activity and follow-up questions grounded in the retrieved passages.
11. The teacher reviews, edits, and approves or rejects the intervention.
12. Follow-up results are recorded or loaded from clearly labeled demo data.
13. The dashboard compares baseline and follow-up performance.

The implementation order and acceptance criteria are maintained in [TASKS.md](../TASKS.md).

## MVP boundaries

The MVP is a focused teacher workflow, not a general school platform. It excludes a full LMS, complex authentication/RBAC, parent and administration portals, attendance, enrollment, payments, messaging, notifications, native mobile apps, gamification, custom model training, microservices, Kubernetes, and elaborate MLOps.

Simple demo-safe access controls may be added if deployment requires them, but they must not displace the golden path.

## Educational safeguards

- **Potential, not proven:** label machine-generated groups as potential misconceptions until a teacher reviews them.
- **Question-specific context:** never group answers from unrelated questions solely because their wording is similar.
- **Evidence first:** show original representative responses and support counts alongside summaries.
- **No invention:** do not invent responses, explanations of student intent, citations, or instructional evidence.
- **Small-sample restraint:** avoid strong conclusions from very small, unstable, or incoherent groups.
- **Teacher authority:** teachers decide whether an interpretation is educationally valid and whether remediation is approved.
- **Grounded intervention:** remediation must use retrieved teacher material or explicitly report that adequate grounding was unavailable.
- **Privacy minimization:** use synthetic identifiers for the demo and avoid unnecessary student personal data.
- **Transparent measurement:** do not imply causality from a simple before/after comparison; report what was measured and what is missing.

## Required error states

| Condition | Required behavior |
|---|---|
| Invalid CSV, unsupported encoding, or missing columns | Reject before analysis; identify the file/schema issue and how to correct it. |
| Empty student response | Preserve an explicit blank status, exclude it from semantic grouping, and show it in counts. |
| Insufficient data for meaningful grouping | Return a successful analysis with an `insufficient_data` outcome and explanation; do not force clusters. |
| Embedding model failure | Mark analysis failed or retryable, preserve input, and offer retry; do not return synthetic vectors or groups. |
| LLM provider failure | Preserve deterministic evidence and show that the interpretation/remediation is unavailable; do not fabricate prose. |
| No sufficiently relevant retrieved material | Show the absence of grounding and prevent grounded-remediation claims; allow the teacher to choose better material. |
| Network or backend failure | Show a retryable message, retain safe local state where possible, and avoid duplicate submissions. |
| Missing follow-up results | Show `not available` and the number missing; never treat missing values as zero. |

Implemented handling and explicitly proposed extensions are separated in [AI_PIPELINE.md](AI_PIPELINE.md); the current API error contract is in [API.md](API.md).

## Hackathon success criteria

- A working teacher interface completes the documented golden path.
- Misconception detection functions on the reproducible demo data.
- Each proposed group includes teacher-verifiable evidence.
- Retrieval works over teacher-provided material.
- Remediation is visibly grounded in retrieved passages.
- The teacher can review, edit, approve, or reject the intervention.
- Baseline and follow-up results are shown honestly.
- Input validation and meaningful error states work.
- The full demonstration is reliable and repeatable.

The result must demonstrate an integrated educational reasoning workflow, not a CRUD application with a chatbot attached.
