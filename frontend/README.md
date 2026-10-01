# ClassLens frontend

React + Vite teacher workspace. Frontend files only.

## Run

Use Node.js 22.13 or newer. Open this folder in VS Code, then run:

```sh
npm install
npm run dev
```

`npm run build` creates the production frontend in `dist/`.

## Structure

- `src/App.jsx` — navigation and current browser-session state
- `src/pages/` — the six teacher pages
- `src/components/` — shared frontend controls and help dialog
- `src/utils/responses.js` — local CSV/JSON parsing and score summaries
- `src/styles.css` — typography, layout, and responsive styles
- `public/assets/` — supplied branding
- `public/fonts/` — local Inter font and its license

There is no backend, database, preset assessment, or fabricated score data. File upload, assessment forms, draft editing, and approval work in the current session. Findings and follow-up results use only supplied data. Practice questions remain empty until provided. Reloading clears the session.

## Response files

CSV headers or JSON keys require `student_id`, `question_id`, and `answer`. Include 3–10,000 responses; maximum file size is 2 MB.

Optional text fields: `question`, `expected_answer`, `misconception`, `misconception_phrase`, and `explanation`. The supplied misconception phrase is highlighted only when it occurs in the student answer. Teacher review accepts or rejects supplied findings; the frontend does not generate analysis.

Optional baseline scores: `score` and `max_score`. Optional follow-up scores: `follow_up_score` and `follow_up_max_score`. Each score requires its corresponding positive maximum; scores range from zero to that maximum. Blank scores remain missing. Before-and-after results compare only responses with both scores, using weighted totals. Student totals and score coverage show incomplete data separately.

## Layout and controls

Content has a small additional desktop inset (12px per side beyond the previous version), with a 1760px maximum width on larger displays. Mobile keeps its original gutter. The supplied navbar, logo crop, navigation spacing, and navigation breakpoints are unchanged. Content uses local Inter and the supplied dark-green branding and mascot.

Language uses keyboard-accessible radio buttons styled as selection chips. Assessment and activity titles use a clean underlined title field. Teacher findings display as a summary card instead of a read-only input. Free-text fields remain for unique class names, topics, explanations, and review notes.

Lesson material supports pasted text or a local TXT/Markdown file (maximum 2 MB). Imported text can be reviewed and edited. Response files also support drag and drop. The assessment readiness strip reflects actual details and uploads. Intervention Review includes a live student explanation preview.
