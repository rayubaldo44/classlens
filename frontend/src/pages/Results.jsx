import {
  ChartNoAxesCombined,
  FileText,
  ArrowRight,
  Users,
  BookOpen,
} from "lucide-react";
import {
  Badge,
  Button,
  EmptyState,
  PageHeading,
  Panel,
  Stat,
} from "../components/ui";

const percent = (value) => (value === null ? "—" : `${Math.round(value)}%`);
function ScoreBar({ label, value, after = false }) {
  return (
    <div className="score-bar-row">
      <span>{label}</span>
      <div
        className={`score-track ${value === null ? "score-track-missing" : ""}`}
        aria-hidden="true"
      >
        {value !== null && (
          <div
            className={`score-fill ${after ? "score-fill-after" : ""}`}
            style={{ width: `${value}%` }}
          />
        )}
      </div>
      <strong>{percent(value)}</strong>
    </div>
  );
}
export default function Results({
  assessment,
  summary,
  activity,
  prepared,
  go,
}) {
  const before = summary.paired ? summary.before : summary.baseline;
  return (
    <>
      <PageHeading
        title="Results"
        action={<img className="page-mascot" src="/assets/mascot.png" alt="" />}
        description={
          prepared
            ? `${assessment.title} · ${assessment.className}`
            : "Review baseline and follow-up performance for your assessment."
        }
      />
      {!prepared ? (
        <Panel title="Assessment results">
          <EmptyState
            icon={ChartNoAxesCombined}
            title="No assessment results yet"
            description="Add an assessment to view its response and score breakdown."
            action={
              <Button onClick={() => go("upload")}>
                Upload assessment
                <ArrowRight size={17} />
              </Button>
            }
          />
        </Panel>
      ) : (
        <>
          <div className="stats-grid">
            <Stat
              icon={Users}
              label="Students"
              value={summary.students}
              detail="Students in this assessment"
            />
            <Stat
              icon={FileText}
              label="Matched students"
              value={summary.matchedStudents}
              detail={
                summary.paired
                  ? `${summary.paired} responses with both scores`
                  : "No matched score pairs yet"
              }
            />
            <Stat
              icon={BookOpen}
              label="Approved activities"
              value={activity.approved ? "1" : "—"}
              detail={
                activity.approved ? activity.title : "Awaiting teacher approval"
              }
            />
          </div>
          <Panel
            title="Before and after"
            detail={
              summary.paired
                ? "Comparison uses the same matched student responses, weighted by maximum score."
                : "Baseline uses uploaded scores. Add follow-up scores to compare."
            }
            action={
              <Badge tone={summary.paired ? "green" : "neutral"}>
                {summary.paired ? "Matched comparison" : "Awaiting follow-up"}
              </Badge>
            }
          >
            <div className="results-comparison">
              <div
                className="score-chart"
                role="img"
                aria-label={`Baseline ${percent(before)}. Follow-up ${percent(summary.after)}. ${summary.paired} matched response pairs.`}
              >
                <ScoreBar label="Baseline" value={before} />
                <ScoreBar label="Follow-up" value={summary.after} after />
                <p>
                  {summary.after === null
                    ? "No matched follow-up scores available"
                    : `${summary.matchedStudents} students · ${summary.paired} matched responses`}
                </p>
              </div>
              <div className="change-summary">
                <span>Score change</span>
                <strong>
                  {summary.change === null
                    ? "—"
                    : `${summary.change > 0 ? "+" : ""}${Math.round(summary.change * 10) / 10}`}
                </strong>
                <small>
                  {summary.change === null
                    ? "Awaiting matched scores"
                    : "percentage points"}
                </small>
              </div>
            </div>
            <div className="score-coverage">
              <span>
                <strong>{summary.missingBaseline}</strong> missing baseline
                scores
              </span>
              <span>
                <strong>{summary.missingFollowUp}</strong> missing follow-up
                scores
              </span>
              <span>Missing scores are excluded from calculations.</span>
            </div>
          </Panel>
          <Panel
            title="Student score breakdown"
            detail="Each total includes only available scores. Zero is a valid score."
            className="section-gap"
          >
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Student ID</th>
                    <th>Baseline</th>
                    <th>Follow-up</th>
                    <th>Score coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.studentScores.map((row) => {
                    const complete = row.pairedCount === row.responseCount;
                    return (
                      <tr key={row.student}>
                        <td className="table-id">{row.student}</td>
                        <td>
                          {row.baselineCount ? (
                            `${row.score} / ${row.total}`
                          ) : (
                            <span className="missing-score">Missing</span>
                          )}
                        </td>
                        <td>
                          {row.followUpCount ? (
                            `${row.followUp} / ${row.followUpTotal}`
                          ) : (
                            <span className="missing-score">Missing</span>
                          )}
                        </td>
                        <td>
                          <Badge tone={complete ? "green" : "neutral"}>
                            {complete
                              ? "Complete"
                              : !row.baselineCount
                                ? "Missing baseline"
                                : !row.followUpCount
                                  ? "Awaiting follow-up"
                                  : "Partial scores"}
                          </Badge>
                          <small className="score-count">
                            {row.baselineCount}/{row.responseCount} baseline ·{" "}
                            {row.followUpCount}/{row.responseCount} follow-up
                          </small>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </>
  );
}
