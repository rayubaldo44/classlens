import {
  BookOpen,
  ListChecks,
  Check,
  Save,
  PencilLine,
  ArrowRight,
} from "lucide-react";
import ChoiceGroup from "../components/ChoiceGroup";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  PageHeading,
  Panel,
} from "../components/ui";

export default function InterventionReview({
  assessment,
  activity,
  updateActivity,
  saveActivity,
  approveActivity,
  go,
}) {
  return (
    <>
      <PageHeading
        title="Intervention Review"
        description="Prepare and review an activity before approving it."
        action={
          <Badge tone={activity.approved ? "green" : "neutral"}>
            {activity.approved
              ? "Approved"
              : activity.saved
                ? "Saved draft"
                : "Draft"}
          </Badge>
        }
      />
      {activity.approved && (
        <div className="approval-confirmation" role="status">
          <img className="approval-mascot" src="/assets/mascot.png" alt="" />
          <div>
            <strong>Activity approved</strong>
            <p>{activity.title} is ready. Check the assessment results next.</p>
          </div>
          <Button secondary onClick={() => go("results")}>
            View results
            <ArrowRight size={16} />
          </Button>
        </div>
      )}
      <form onSubmit={saveActivity}>
        <div className="detail-grid activity-grid">
          <Panel
            title="Activity details"
            detail="Use your lesson material to write a focused explanation."
          >
            <div className="form-stack">
              <div className="activity-heading-fields">
                <Field label="Activity title">
                  <input
                    required
                    value={activity.title}
                    onChange={(e) => updateActivity("title", e.target.value)}
                    className="title-input"
                    placeholder="Give this activity a title"
                    maxLength={100}
                  />
                </Field>
                <ChoiceGroup
                  label="Language"
                  options={["English", "Filipino", "Taglish"]}
                  value={activity.language}
                  onChange={(value) => updateActivity("language", value)}
                />
              </div>
              <div className="document-editor">
                <div className="document-toolbar">
                  <PencilLine size={15} />
                  <span>Student explanation</span>
                  <small>Editable draft</small>
                </div>
                <Field label="Explanation">
                  <textarea
                    required
                    rows={7}
                    value={activity.explanation}
                    onChange={(e) =>
                      updateActivity("explanation", e.target.value)
                    }
                    placeholder="Write the explanation students should read"
                  />
                </Field>
              </div>
            </div>
            <div className="editor-note">
              <PencilLine size={16} />
              <span>You can edit the explanation before approval.</span>
            </div>
          </Panel>
          <div className="side-stack">
            <Panel
              title="Student preview"
              detail="How your explanation reads to the class."
              action={<Badge>{activity.language}</Badge>}
              className="activity-preview-panel"
            >
              <div className="activity-preview">
                <span>LEARNING ACTIVITY</span>
                <h3>{activity.title || "Your activity title"}</h3>
                <p
                  className={activity.explanation ? "" : "preview-placeholder"}
                >
                  {activity.explanation ||
                    "Start writing your explanation. Your draft will appear here as you type."}
                </p>
              </div>
            </Panel>
            <Panel title="Lesson reference">
              <details className="reference-details" open={!assessment.lesson}>
                <summary>
                  <BookOpen size={16} /> Read lesson reference
                </summary>
                <div className="lesson-reference">
                  <BookOpen size={19} />
                  <p>
                    {assessment.lesson ||
                      "Add your lesson material in Upload Assessment to use it here."}
                  </p>
                </div>
              </details>
            </Panel>
            <Panel
              className="practice-panel"
              title="Practice questions"
              detail="Questions linked to this activity."
            >
              <EmptyState
                compact
                icon={ListChecks}
                title="No questions available"
                description="Practice questions will appear here when they are added to the activity."
              />
            </Panel>
          </div>
        </div>
        <div className="form-actions">
          <p>
            {activity.approved
              ? "This activity has been approved."
              : "Save your draft before approving the activity."}
          </p>
          <div className="action-group">
            <Button
              secondary
              type="submit"
              disabled={!activity.title.trim() || !activity.explanation.trim()}
            >
              <Save size={17} />
              Save draft
            </Button>
            <Button
              onClick={approveActivity}
              disabled={!activity.saved || activity.approved}
            >
              <Check size={17} />
              {activity.approved ? "Approved" : "Approve activity"}
            </Button>
          </div>
        </div>
      </form>
    </>
  );
}
