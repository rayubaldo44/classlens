import { cloneElement, createElement, useId } from "react";

export function Button({
  children,
  secondary = false,
  className = "",
  type = "button",
  ...props
}) {
  return (
    <button
      type={type}
      className={`button ${secondary ? "button-secondary" : "button-primary"} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Badge({ children, tone = "neutral" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function PageHeading({ title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

export function Panel({ title, detail, action, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {detail && <p>{detail}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  compact = false,
}) {
  return (
    <div className={`empty-state ${compact ? "empty-compact" : ""}`}>
      <span className="empty-icon">
        {createElement(Icon, { size: 24, strokeWidth: 1.6 })}
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function Stat({ icon: Icon, label, value, detail }) {
  return (
    <div className="stat">
      <div className="stat-top">
        <span>{label}</span>
        {createElement(Icon, { size: 19, strokeWidth: 1.7 })}
      </div>
      <strong>{value}</strong>
      <p>{detail}</p>
    </div>
  );
}

export function Field({ label, children, hint }) {
  const id = useId();
  return (
    <label className="field">
      <span id={`${id}-label`}>{label}</span>
      {cloneElement(children, {
        "aria-labelledby": `${id}-label`,
        "aria-describedby": hint ? `${id}-hint` : undefined,
      })}
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </label>
  );
}
