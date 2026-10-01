import { useRef, useState } from "react";
import { FileText, FileUp, PencilLine, LoaderCircle, X } from "lucide-react";
import ChoiceGroup from "./ChoiceGroup";
import { Button, Field } from "./ui";

export default function LessonMaterial({ value, onChange, disabled }) {
  const [mode, setMode] = useState("Paste text");
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");
  const [reading, setReading] = useState(false);
  const input = useRef(null);
  const pending = useRef(false);
  async function readFile(file) {
    if (!file || pending.current || disabled) return;
    setError("");
    if (!/\.(txt|md)$/i.test(file.name)) {
      setError("Choose a plain text (.txt) or Markdown (.md) file.");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError("Lesson files must be 2 MB or smaller.");
      return;
    }
    pending.current = true;
    setReading(true);
    try {
      const text = await file.text();
      if (!text.trim()) throw new Error("This lesson file is empty.");
      if (text.includes("\u0000"))
        throw new Error("Use a plain text lesson file.");
      onChange(text);
      setFileName(file.name);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not read this file. Try again.",
      );
    } finally {
      pending.current = false;
      setReading(false);
    }
  }
  return (
    <div className="lesson-material" aria-busy={reading}>
      <div className="material-heading">
        <span className="field-title">
          Lesson material <small>Optional</small>
        </span>
        <p>Add a reference for the teacher review.</p>
      </div>
      <ChoiceGroup
        label="Add lesson material using"
        options={["Paste text", "Upload file"]}
        value={mode}
        onChange={setMode}
        disabled={disabled || reading}
      />
      {mode === "Upload file" && (
        <div
          className="lesson-file-zone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            void readFile(e.dataTransfer.files?.[0]);
          }}
        >
          <FileUp size={23} strokeWidth={1.6} />
          <div>
            <strong>
              {reading ? "Reading lesson…" : "Drop your lesson file here"}
            </strong>
            <p>TXT or Markdown · up to 2 MB</p>
          </div>
          <Button
            secondary
            disabled={disabled || reading}
            onClick={() => input.current?.click()}
          >
            {reading ? (
              <LoaderCircle size={16} className="spin" />
            ) : (
              "Choose file"
            )}
          </Button>
          <input
            ref={input}
            type="file"
            className="sr-only"
            disabled={disabled || reading}
            accept=".txt,.md,text/plain,text/markdown"
            aria-label="Upload lesson material"
            onChange={(e) => {
              void readFile(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </div>
      )}
      {error && (
        <p className="lesson-error" role="alert">
          {error}
        </p>
      )}
      {fileName && value && (
        <div className="lesson-file-name" role="status">
          <FileText size={15} />
          <span>{fileName}</span>
          <button
            type="button"
            className="icon-button"
            disabled={disabled || reading}
            aria-label="Clear lesson material"
            onClick={() => {
              onChange("");
              setFileName("");
              setError("");
            }}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {(mode === "Paste text" || value) && (
        <div className="document-editor">
          <div className="document-toolbar">
            <PencilLine size={15} />
            <span>
              {mode === "Paste text"
                ? "Lesson reference"
                : "Review and edit imported text"}
            </span>
            <small>
              {value.trim()
                ? `${value.trim().split(/\s+/).length} words`
                : "Text reference"}
            </small>
          </div>
          <Field label="Lesson text">
            <textarea
              disabled={disabled || reading}
              rows={6}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder="Paste the lesson or reference passage here…"
            />
          </Field>
        </div>
      )}
    </div>
  );
}
