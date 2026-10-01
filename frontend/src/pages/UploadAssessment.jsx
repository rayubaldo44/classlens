import {
  Upload,
  FileText,
  X,
  ArrowRight,
  LoaderCircle,
  CircleAlert,
  CheckCircle2,
  Circle,
} from "lucide-react";
import LessonMaterial from "../components/LessonMaterial";
import BrandNote from "../components/BrandNote";
import { Badge, Button, Field, PageHeading, Panel } from "../components/ui";

export default function UploadAssessment({
  assessment,
  updateAssessment,
  responses,
  fileName,
  summary,
  busy,
  error,
  uploadResponses,
  removeFile,
  saveAssessment,
}) {
  const readiness = [
    {
      label: "Class details",
      done: Boolean(
        assessment.title.trim() &&
          assessment.className.trim() &&
          assessment.topic.trim(),
      ),
    },
    { label: "Student responses", done: responses.length > 0 },
    {
      label: "Ready to review",
      done: Boolean(
        assessment.title.trim() &&
          assessment.className.trim() &&
          assessment.topic.trim() &&
          responses.length,
      ),
    },
  ];
  return (
    <>
      <PageHeading
        title="Upload Assessment"
        description="Add your class details, lesson material, and student responses."
      />
      <div className="upload-readiness" aria-label="Assessment readiness">
        {readiness.map(({ label, done }, index) => (
          <div key={label} className={done ? "readiness-done" : ""}>
            {done ? <CheckCircle2 size={17} /> : <Circle size={17} />}
            <span>{label}</span>
            <small>
              {done
                ? index === 2
                  ? "Ready"
                  : "Added"
                : index === 2
                  ? "Save when complete"
                  : "To add"}
            </small>
          </div>
        ))}
      </div>
      <form onSubmit={saveAssessment} aria-busy={busy}>
        <div className="upload-grid">
          <Panel
            className="assessment-editor-panel"
            title="Assessment details"
            detail="Give this assessment a clear name."
          >
            <div className="form-stack">
              <Field label="Assessment title">
                <input
                  required
                  disabled={busy}
                  value={assessment.title}
                  onChange={(e) => updateAssessment("title", e.target.value)}
                  className="title-input"
                  placeholder="e.g. Understanding fractions"
                  maxLength={100}
                />
              </Field>
              <div className="form-row">
                <Field label="Class">
                  <input
                    required
                    disabled={busy}
                    value={assessment.className}
                    onChange={(e) =>
                      updateAssessment("className", e.target.value)
                    }
                    placeholder="e.g. Grade 7 · Section A"
                    maxLength={80}
                  />
                </Field>
                <Field label="Learning topic">
                  <input
                    required
                    disabled={busy}
                    value={assessment.topic}
                    onChange={(e) => updateAssessment("topic", e.target.value)}
                    placeholder="e.g. Equivalent fractions"
                    maxLength={100}
                  />
                </Field>
              </div>
              <div className="form-divider" />
              <LessonMaterial
                value={assessment.lesson}
                onChange={(value) => updateAssessment("lesson", value)}
                disabled={busy}
              />
            </div>
          </Panel>
          <Panel
            title="Student responses"
            detail="Use anonymized student IDs in your file."
            action={
              responses.length > 0 && <Badge tone="green">File added</Badge>
            }
          >
            <label
              className={`upload-zone ${busy ? "upload-busy" : ""}`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (!busy) void uploadResponses(e.dataTransfer.files?.[0]);
              }}
            >
              <span className="upload-icon">
                {busy ? (
                  <LoaderCircle size={26} className="spin" />
                ) : (
                  <Upload size={26} strokeWidth={1.6} />
                )}
              </span>
              <strong>
                {busy ? "Reading your file…" : "Drop student responses here"}
              </strong>
              <span>or browse from your device</span>
              <small>CSV or JSON · maximum 2 MB</small>
              <span className="upload-choice">Browse files</span>
              <input
                type="file"
                accept=".csv,.json"
                disabled={busy}
                aria-label="Choose student response file"
                onChange={(e) => {
                  void uploadResponses(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </label>
            {fileName && (
              <div className="file-summary" role="status">
                <FileText size={21} />
                <div>
                  <strong>{fileName}</strong>
                  <span>
                    {responses.length} responses · {summary.students} students
                  </span>
                </div>
                <button
                  type="button"
                  className="icon-button"
                  disabled={busy}
                  onClick={removeFile}
                  aria-label="Remove response file"
                >
                  <X size={18} />
                </button>
              </div>
            )}
            <div className="file-format">
              <h3>Required columns</h3>
              <div className="column-labels">
                <code>student_id</code>
                <code>question_id</code>
                <code>answer</code>
              </div>
              <p>Add scores or response findings using optional columns.</p>
              <p>Include at least three responses.</p>
              <details className="optional-columns">
                <summary>Additional data columns</summary>
                <p>
                  Baseline: <code>score</code>, <code>max_score</code>.
                </p>
                <p>
                  Follow-up: <code>follow_up_score</code>,{" "}
                  <code>follow_up_max_score</code>.
                </p>
                <p>
                  Evidence: <code>question</code>, <code>expected_answer</code>,{" "}
                  <code>misconception</code>, <code>misconception_phrase</code>,{" "}
                  <code>explanation</code>.
                </p>
              </details>
            </div>
            <BrandNote
              className="upload-brand-note"
              title={
                responses.length
                  ? "Ready for your review"
                  : "Start with student responses"
              }
            >
              {responses.length
                ? "Save the assessment to review the response evidence in Analysis."
                : "Choose your response file and add the class details to begin."}
            </BrandNote>
          </Panel>
        </div>
        {error && (
          <div role="alert" className="error-message">
            <CircleAlert size={18} />
            {error}
          </div>
        )}
        <div className="form-actions">
          <p>
            {responses.length
              ? `${responses.length} responses ready to review`
              : "Add a response file to continue."}
          </p>
          <Button type="submit" disabled={busy || !responses.length}>
            Save assessment
            <ArrowRight size={17} />
          </Button>
        </div>
      </form>
    </>
  );
}
