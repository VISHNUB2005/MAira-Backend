export default function Card({
  children,
  title,
  className = "",
}) {
  return (
    <section
      className={className}
      style={{
        background: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        borderRadius: "12px",
        padding: "24px",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
        color: "#ffffff",
      }}
    >
      {title && (
        <h2 style={{ marginTop: 0, marginBottom: "20px", fontSize: "20px", fontWeight: "600" }}>
          {title}
        </h2>
      )}
      {children}
    </section>
  );
}