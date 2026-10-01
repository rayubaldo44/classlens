import {
  Plus,
  FileText,
  Users,
  BookOpen,
  Upload,
  ArrowUpRight,
  CheckCircle2,
  ScanLine,
} from "lucide-react";
import {
  Badge,
  Button,
  EmptyState,
  PageHeading,
  Panel,
  Stat,
} from "../components/ui";

export default function Dashboard({
  assessment,
  responses,
  summary,
  prepared,
  activity,
  go,
  newAssessment,
  busy,
  findings,
  reviewedCount,
  reviewComplete,
  selectResponse,
}) {
  const hasAssessment = Boolean(assessment.title.trim() || responses.length);
  const steps = [
    {
      title: "Upload assessment",
      detail: responses.length
        ? `${responses.length} responses added`
        : "Add class details and responses",
      complete: prepared,
      view: "upload",
    },
    {
      title: "Review misconceptions",
      detail: findings.length
        ? `${reviewedCount} of ${findings.length} reviewed`
        : "Awaiting analysis",
      complete: reviewComplete,
      view: "analysis",
    },
    {
      title: "Review intervention",
      detail: activity.approved
        ? "Activity approved"
        : activity.saved
          ? "Draft saved for review"
          : "Prepare a targeted activity",
      complete: activity.approved,
      view: "intervention",
    },
    {
      title: "Check results",
      detail: summary.paired
        ? `${summary.paired} matched response scores`
        : "Awaiting follow-up scores",
      complete:
        summary.paired > 0 &&
        summary.missingFollowUp === 0 &&
        summary.missingBaseline === 0,
      view: "results",
    },
  ];
  return (
    <>
      <PageHeading
        title="Dashboard"
        description="Manage your assessments and review what your class needs next."
        action={
          <Button onClick={newAssessment} disabled={busy}>
            <Plus size={18} />
            New assessment
          </Button>
        }
      />
      <div className="stats-grid">
        <Stat
          icon={FileText}
          label="Student responses"
          value={responses.length || "—"}
          detail={
            responses.length
              ? "Responses in the current assessment"
              : "Upload an assessment to begin"
          }
        />
        <Stat
          icon={Users}
          label="Students"
          value={summary.students || "—"}
          detail={
            summary.students
              ? "Unique students in your response file"
              : "No student responses added"
          }
        />
        <Stat
          icon={BookOpen}
          label="Approved activities"
          value={activity.approved ? "1" : "—"}
          detail={
            activity.approved
              ? "Reviewed and approved by you"
              : "No approved activity yet"
          }
        />
      </div>
      <div className="dashboard-grid">
        <Panel
          title="Current assessment"
          detail="Your class details and response file."
          action={
            hasAssessment && (
              <Badge tone={prepared ? "green" : "neutral"}>
                {prepared ? "Uploaded" : "Draft"}
              </Badge>
            )
          }
        >
          {hasAssessment ? (
            <div className="assessment-content">
              <div className="assessment-identity">
                <span className="document-icon">
                  <FileText size={24} />
                </span>
                <div>
                  <h3>{assessment.title || "Untitled assessment"}</h3>
                  <p>{assessment.className || "Class not added"}</p>
                </div>
                <img
                  className="assessment-mascot"
                  src="/assets/mascot.png"
                  alt="ClassLens mascot"
                />
              </div>
              <dl className="assessment-facts">
                <div>
                  <dt>Learning topic</dt>
                  <dd>{assessment.topic || "Not added"}</dd>
                </div>
                <div>
                  <dt>Responses</dt>
                  <dd>{responses.length || "Not added"}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{prepared ? "Ready to review" : "In progress"}</dd>
                </div>
              </dl>
              <div className="panel-bottom">
                <Button
                  secondary
                  onClick={() => go(prepared ? "analysis" : "upload")}
                >
                  {prepared ? "View assessment" : "Continue assessment"}
                  <ArrowUpRight size={16} />
                </Button>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={Upload}
              title="Add your first assessment"
              description="Upload student responses to keep your assessment and teacher review in one place."
              action={
                <Button onClick={() => go("upload")}>
                  <Plus size={17} />
                  Upload assessment
                </Button>
              }
            />
          )}
        </Panel>
        <Panel
          title="Review progress"
          detail="A clear next step for every assessment."
        >
          <div className="progress-list">
            {steps.map((step, index) => (
              <button
                type="button"
                className="progress-row"
                key={step.view}
                onClick={() => go(step.view)}
              >
                <span
                  className={`step-marker ${step.complete ? "step-complete" : ""}`}
                >
                  {step.complete ? <CheckCircle2 size={18} /> : index + 1}
                </span>
                <span className="progress-copy">
                  <strong>{step.title}</strong>
                  <small>{step.detail}</small>
                </span>
                <ArrowUpRight size={16} />
              </button>
            ))}
          </div>
          <div className="progress-note">
            <img src="/assets/mascot.png" alt="" />
            <p>Review the evidence before deciding on an activity.</p>
          </div>
        </Panel>
      </div>
      <Panel
        title="Learning gaps"
        action={
          <Badge>
            {findings.length
              ? `${findings.length} findings`
              : "Awaiting analysis"}
          </Badge>
        }
        className="dashboard-gaps"
      >
        {findings.length ? (
          <div className="findings-list">
            {findings.slice(0, 3).map((row) => (
              <button
                type="button"
                className="finding-row"
                key={row.index}
                onClick={() => selectResponse(row.index)}
              >
                <span>
                  <small>
                    Student {row.student_id} · Question {row.question_id}
                  </small>
                  <strong>{row.misconception}</strong>
                </span>
                <ArrowUpRight size={16} />
              </button>
            ))}
          </div>
        ) : (
          <div className="inline-empty">
            <ScanLine size={22} />
            <div>
              <h3>No findings available yet</h3>
              <p>Upload response findings to begin your evidence review.</p>
            </div>
            <Button secondary onClick={() => go("analysis")}>
              View analysis
              <ArrowUpRight size={16} />
            </Button>
          </div>
        )}
      </Panel>
    </>
  );
}
