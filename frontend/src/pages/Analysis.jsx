import {
  ScanLine,
  FileText,
  Users,
  ListChecks,
  ArrowRight,
  FileUp,
} from "lucide-react";
import {
  Badge,
  Button,
  EmptyState,
  PageHeading,
  Panel,
  Stat,
} from "../components/ui";

export default function Analysis({
  assessment,
  responses,
  prepared,
  summary,
  go,
  findings,
  reviews,
  selectResponse,
}) {
  return (
    <>
      <PageHeading
        title="Analysis"
        description={
          prepared
            ? `${assessment.title} · ${assessment.className}`
            : "Review your assessment responses and potential misconceptions."
        }
        action={
          <Button secondary onClick={() => go("upload")}>
            <FileUp size={17} />
            {responses.length ? "Edit assessment" : "Upload assessment"}
          </Button>
        }
      />
      {!prepared ? (
        <Panel title="Assessment overview">
          <EmptyState
            icon={ScanLine}
            title={
              responses.length
                ? "Finish your assessment details"
                : "No assessment ready for review"
            }
            description={
              responses.length
                ? "Save your class details and responses before reviewing this assessment."
                : "Upload a response file and add your class details to begin."
            }
            action={
              <Button onClick={() => go("upload")}>
                Go to Upload Assessment
                <ArrowRight size={17} />
              </Button>
            }
          />
        </Panel>
      ) : (
        <>
          <div className="stats-grid">
            <Stat
              icon={FileText}
              label="Responses"
              value={responses.length}
              detail="Answers in your uploaded file"
            />
            <Stat
              icon={Users}
              label="Students"
              value={summary.students}
              detail="Unique student IDs"
            />
            <Stat
              icon={ListChecks}
              label="Questions"
              value={summary.questions}
              detail="Unique assessment questions"
            />
          </div>
          <Panel
            title="Potential misconceptions"
            detail="Review each finding against the response evidence."
            action={
              <Badge>
                {findings.length
                  ? `${findings.length} findings`
                  : "Awaiting analysis"}
              </Badge>
            }
          >
            {findings.length ? (
              <div className="findings-list">
                {findings.map((row) => (
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
                    <Badge
                      tone={
                        reviews[row.index] === "accepted" ? "green" : "neutral"
                      }
                    >
                      {reviews[row.index] === "accepted"
                        ? "Accepted"
                        : reviews[row.index] === "rejected"
                          ? "Rejected"
                          : "Awaiting review"}
                    </Badge>
                    <ArrowRight size={17} />
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState
                compact
                icon={ScanLine}
                title="No findings available"
                description="Uploaded findings will appear here. You can still inspect each student response below."
              />
            )}
          </Panel>
          <Panel
            title="Student responses"
            detail={`Showing ${Math.min(responses.length, 20)} of ${responses.length} responses.`}
            className="section-gap"
          >
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Student ID</th>
                    <th>Question</th>
                    <th>Response</th>
                    <th>Score</th>
                    <th>
                      <span className="sr-only">Review response</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {responses.slice(0, 20).map((row, index) => (
                    <tr key={index}>
                      <td className="table-id">{row.student_id}</td>
                      <td>{row.question_id}</td>
                      <td className="response-cell">{row.answer}</td>
                      <td>
                        {row.score === undefined
                          ? "—"
                          : `${row.score} / ${row.max_score}`}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="table-action"
                          onClick={() => selectResponse(index)}
                        >
                          View response
                          <ArrowRight size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </>
  );
}
