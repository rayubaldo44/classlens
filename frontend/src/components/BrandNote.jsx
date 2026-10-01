export default function BrandNote({ title, children, className = "" }) {
  return (
    <aside className={`brand-note ${className}`}>
      <img src="/assets/mascot.png" alt="" />
      <div>
        <strong>{title}</strong>
        <p>{children}</p>
      </div>
    </aside>
  );
}
