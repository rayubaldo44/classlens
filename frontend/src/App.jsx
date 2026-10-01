import { useState } from "react";
import {
  LayoutDashboard,
  FileUp,
  ScanLine,
  Lightbulb,
  BookOpen,
  ChartNoAxesCombined,
  CircleHelp,
  GraduationCap,
} from "lucide-react";
import { Toaster, toast } from "sonner";
import { Badge, Button } from "./components/ui";
import { HelpDialog } from "./components/HelpDialog";
import { readResponseFile, summarizeResponses } from "./utils/responses";
import Dashboard from "./pages/Dashboard";
import UploadAssessment from "./pages/UploadAssessment";
import Analysis from "./pages/Analysis";
import MisconceptionDetail from "./pages/MisconceptionDetail";
import InterventionReview from "./pages/InterventionReview";
import Results from "./pages/Results";

const navigation = [
  { view: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { view: "upload", label: "Upload Assessment", icon: FileUp },
  { view: "analysis", label: "Analysis", icon: ScanLine },
  { view: "detail", label: "Misconception Detail", icon: Lightbulb },
  { view: "intervention", label: "Intervention Review", icon: BookOpen },
  { view: "results", label: "Results", icon: ChartNoAxesCombined },
];
const emptyAssessment = { title: "", className: "", topic: "", lesson: "" };
const emptyActivity = {
  title: "",
  language: "English",
  explanation: "",
  saved: false,
  approved: false,
};

export default function App() {
  const [view, setView] = useState("dashboard");
  const [assessment, setAssessment] = useState(emptyAssessment);
  const [responses, setResponses] = useState([]);
  const [fileName, setFileName] = useState("");
  const [prepared, setPrepared] = useState(false);
  const [activity, setActivity] = useState(emptyActivity);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [help, setHelp] = useState(false);
  const [selectedResponse, setSelectedResponse] = useState(null);
  const [reviews, setReviews] = useState({});
  const [reviewNotes, setReviewNotes] = useState({});
  const summary = summarizeResponses(responses);
  const findings = prepared
    ? responses.flatMap((row, index) =>
        row.misconception ? [{ ...row, index }] : [],
      )
    : [];
  const reviewedCount = findings.filter(
    (row) =>
      reviews[row.index] === "accepted" || reviews[row.index] === "rejected",
  ).length;
  const reviewComplete =
    findings.length > 0 && reviewedCount === findings.length;
  const stage = !responses.length
    ? "No assessment"
    : !prepared
      ? "Uploaded · finish details"
      : activity.approved
        ? "Activity approved"
        : reviewComplete
          ? "Findings reviewed"
          : findings.length
            ? "Awaiting review"
            : "Uploaded · awaiting analysis";
  const selected = prepared ? responses[selectedResponse] : undefined;
  function resetReview() {
    setSelectedResponse(null);
    setReviews({});
    setReviewNotes({});
  }
  function selectResponse(index) {
    setSelectedResponse(index);
    go("detail");
  }
  function updateReviewNote(value) {
    setReviewNotes((current) => ({ ...current, [selectedResponse]: value }));
    setReviews((current) => ({ ...current, [selectedResponse]: "pending" }));
    setActivity((current) => ({ ...current, saved: false, approved: false }));
  }
  function reviewFinding(status) {
    if (!selected?.misconception) return;
    setReviews((current) => ({ ...current, [selectedResponse]: status }));
    setActivity((current) => ({ ...current, saved: false, approved: false }));
    toast.success(
      status === "accepted" ? "Finding accepted" : "Finding rejected",
    );
  }
  const currentPage = navigation.find((item) => item.view === view);

  function go(nextView) {
    setView(nextView);
    setError("");
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  function newAssessment() {
    if (busy) return;
    setAssessment(emptyAssessment);
    resetReview();
    setResponses([]);
    setFileName("");
    setPrepared(false);
    setActivity(emptyActivity);
    go("upload");
  }
  function updateAssessment(field, value) {
    setAssessment((current) => ({ ...current, [field]: value }));
    setPrepared(false);
    setActivity((current) => ({ ...current, saved: false, approved: false }));
  }
  async function uploadResponses(file) {
    if (!file || busy) return;
    setError("");
    setBusy(true);
    try {
      const imported = await readResponseFile(file);
      resetReview();
      setResponses(imported);
      setFileName(file.name);
      setPrepared(false);
      setActivity(emptyActivity);
      toast.success(`${imported.length} responses added`);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "This file could not be read. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  function removeFile() {
    resetReview();
    setResponses([]);
    setFileName("");
    setPrepared(false);
    setActivity(emptyActivity);
    setError("");
  }
  function saveAssessment(event) {
    event.preventDefault();
    if (
      !assessment.title.trim() ||
      !assessment.className.trim() ||
      !assessment.topic.trim()
    ) {
      setError("Add an assessment title, class, and learning topic.");
      return;
    }
    if (!responses.length) {
      setError("Add a response file before saving the assessment.");
      return;
    }
    setPrepared(true);
    toast.success("Assessment ready to review");
    go("analysis");
  }
  function updateActivity(field, value) {
    setActivity((current) => ({
      ...current,
      [field]: value,
      saved: false,
      approved: false,
    }));
  }
  function saveActivity(event) {
    event.preventDefault();
    if (!activity.title.trim() || !activity.explanation.trim()) return;
    setActivity((current) => ({ ...current, saved: true, approved: false }));
    toast.success("Activity draft saved");
  }
  function approveActivity() {
    if (
      !activity.saved ||
      !activity.title.trim() ||
      !activity.explanation.trim()
    )
      return;
    setActivity((current) => ({ ...current, approved: true }));
    toast.success("Activity approved");
  }

  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="header">
        <div className="header-inner">
          <button
            className="brand"
            aria-label="ClassLens overview"
            onClick={() => go("dashboard")}
          >
            <span className="brand-logo-window">
              <img src="/assets/classlens-logo-current.png" alt="ClassLens" />
            </span>
          </button>
          <nav className="desktop-nav" aria-label="Main navigation">
            {navigation.map((n) => (
              <button
                key={n.view}
                onClick={() => go(n.view)}
                className={view === n.view ? "active" : ""}
                aria-current={view === n.view ? "page" : undefined}
              >
                <n.icon size={17} />
                {n.label}
              </button>
            ))}
          </nav>
          <div className="header-end">
            <button
              onClick={() => setHelp(true)}
              className="icon-btn"
              aria-label="How to use ClassLens"
            >
              <CircleHelp size={21} />
            </button>
          </div>
        </div>
      </header>
      <nav className="mobile-nav" aria-label="Mobile navigation">
        {navigation.map((n) => (
          <button
            key={n.view}
            onClick={() => go(n.view)}
            className={view === n.view ? "active" : ""}
            aria-current={view === n.view ? "page" : undefined}
          >
            <n.icon size={19} />
            <span>{n.label}</span>
          </button>
        ))}
      </nav>
      <main id="main" className="page-container">
        <div className="workspace-bar">
          <div className="workspace-status">
            <span className="workspace-label">
              <GraduationCap size={16} />
              Teacher workspace
            </span>
            <Badge
              tone={activity.approved || reviewComplete ? "green" : "neutral"}
            >
              {stage}
            </Badge>
          </div>
          <span className="workspace-location">
            ClassLens<span>/</span>
            {currentPage.label}
          </span>
        </div>
        {view === "dashboard" && (
          <Dashboard
            {...{
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
            }}
          />
        )}
        {view === "upload" && (
          <UploadAssessment
            {...{
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
            }}
          />
        )}
        {view === "analysis" && (
          <Analysis
            {...{
              assessment,
              responses,
              prepared,
              summary,
              go,
              findings,
              reviews,
              selectResponse,
            }}
          />
        )}
        {view === "detail" && (
          <MisconceptionDetail
            {...{ assessment, go, selected, reviewFinding, updateReviewNote }}
            reviewStatus={reviews[selectedResponse] || "pending"}
            reviewNote={
              reviewNotes[selectedResponse] ?? selected?.explanation ?? ""
            }
          />
        )}
        {view === "intervention" && (
          <InterventionReview
            {...{
              assessment,
              activity,
              updateActivity,
              saveActivity,
              approveActivity,
              go,
            }}
          />
        )}
        {view === "results" && (
          <Results {...{ assessment, summary, activity, prepared, go }} />
        )}
        <footer className="page-footer">
          <span>ClassLens</span>
          <span>Teacher workspace</span>
        </footer>
      </main>
      <HelpDialog open={help} onClose={() => setHelp(false)}>
        <h2 id="help-title">Your assessment workspace</h2>
        <p className="dialog-description">
          Keep your class responses and teacher review organized.
        </p>
        <ol className="help-steps">
          <li>
            <strong>Upload an assessment</strong>
            <span>
              Add class details, lesson material, and a CSV or JSON response
              file.
            </span>
          </li>
          <li>
            <strong>Review the evidence</strong>
            <span>
              Use Analysis and Misconception Detail to review findings when
              available.
            </span>
          </li>
          <li>
            <strong>Review an activity</strong>
            <span>
              Edit the explanation, save your draft, and approve it when ready.
            </span>
          </li>
          <li>
            <strong>Check results</strong>
            <span>
              Review uploaded scores and follow-up performance when available.
            </span>
          </li>
        </ol>
        <Button onClick={() => setHelp(false)}>Got it</Button>
      </HelpDialog>
      <Toaster
        position="bottom-right"
        theme="light"
        style={{ fontFamily: "Inter, sans-serif" }}
      />
    </div>
  );
}
