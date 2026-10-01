import {
  ArrowLeft,
  ArrowRight,
  Check,
  X,
  BookOpen,
  Lightbulb,
} from "lucide-react";
import { Badge, Button, Field, PageHeading, Panel } from "../components/ui";
import BrandNote from "../components/BrandNote";
import AnswerComparison from "../components/AnswerComparison";

export default function MisconceptionDetail({
  assessment,
  go,
  selected,
  reviewStatus,
  reviewNote,
  reviewFinding,
  updateReviewNote,
}) {
  const hasFinding = Boolean(selected?.misconception);
  const reviewed = reviewStatus !== "pending";
  return (
    <>
      <button
        type="button"
        className="back-link"
        onClick={() => go("analysis")}
      >
        <ArrowLeft size={16} />
        Back to analysis
      </button>
      <PageHeading
        title="Misconception Detail"
        description="See the difference. Review the idea behind the student’s answer."
      />
      <div className="detail-grid evidence-grid">
        <Panel
          className="evidence-panel"
          title="Response evidence"
          action={
            <Badge tone={reviewStatus === "accepted" ? "green" : "neutral"}>
              {hasFinding
                ? reviewed
                  ? reviewStatus === "accepted"
                    ? "Accepted"
                    : "Rejected"
                  : "Awaiting review"
                : selected
                  ? "Response selected"
                  : "No response selected"}
            </Badge>
          }
        >
          {selected && (
            <div className="evidence-question">
              <span>
                Student {selected.student_id} · Question {selected.question_id}
              </span>
              <h3>{selected.question || `Question ${selected.question_id}`}</h3>
            </div>
          )}
          <AnswerComparison response={selected} />
          {hasFinding ? (
            <div className="finding-callout">
              <Lightbulb size={19} />
              <div>
                <span>Flagged idea</span>
                <h3>{selected.misconception}</h3>
                {selected.misconception_phrase &&
                  !selected.answer
                    .toLocaleLowerCase()
                    .includes(
                      selected.misconception_phrase.toLocaleLowerCase(),
                    ) && (
                    <p>
                      The supplied highlight phrase was not found in this
                      answer.
                    </p>
                  )}
              </div>
            </div>
          ) : (
            <p className="comparison-note">
              {selected
                ? "This response has no misconception finding supplied."
                : "Choose a response or finding to compare the evidence."}
            </p>
          )}
          {!selected && (
            <Button secondary onClick={() => go("analysis")}>
              Choose a response
              <ArrowRight size={16} />
            </Button>
          )}
          <div className="reference-box">
            <BookOpen size={18} />
            <div>
              <strong>Lesson reference</strong>
              <p>
                {assessment.lesson ||
                  "Add lesson material in your assessment details."}
              </p>
            </div>
          </div>
        </Panel>
        <Panel
          title="Teacher review"
          detail="Confirm whether the evidence supports the flagged idea."
        >
          <div className="form-stack">
            <div className="finding-summary">
              <span>
                <Lightbulb size={15} /> Finding to review
              </span>
              <p>
                {selected?.misconception ||
                  "Select a finding from Analysis to begin."}
              </p>
            </div>
            <Field
              label="Review note"
              hint="Add or edit your reasoning before continuing."
            >
              <textarea
                rows={4}
                disabled={!hasFinding}
                value={reviewNote}
                onChange={(event) => updateReviewNote(event.target.value)}
                placeholder="Explain why you accept or reject this finding"
              />
            </Field>
          </div>
          <div className="review-actions">
            <Button
              disabled={!hasFinding || reviewStatus === "accepted"}
              onClick={() => reviewFinding("accepted")}
            >
              <Check size={17} />
              Accept finding
            </Button>
            <Button
              secondary
              disabled={!hasFinding || reviewStatus === "rejected"}
              onClick={() => reviewFinding("rejected")}
            >
              <X size={17} />
              Reject finding
            </Button>
          </div>
          {reviewed && (
            <p className="review-confirmation" role="status">
              {reviewStatus === "accepted"
                ? "Finding accepted. Prepare a targeted activity next."
                : "Finding rejected. Return to Analysis to review another response."}
            </p>
          )}
          {reviewStatus === "accepted" && (
            <Button
              className="continue-action"
              onClick={() => go("intervention")}
            >
              Review intervention
              <ArrowRight size={16} />
            </Button>
          )}
          <BrandNote
            className="review-brand-note"
            title="Review the idea behind the answer"
          >
            Use the student and expected answers as evidence before accepting a
            finding.
          </BrandNote>
        </Panel>
      </div>
    </>
  );
}
