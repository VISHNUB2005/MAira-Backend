const variants = {
  success: {
    background: "rgba(16, 185, 129, 0.15)",
    color: "#34d399",
    border: "1px solid rgba(16, 185, 129, 0.3)",
  },
  error: {
    background: "rgba(239, 68, 68, 0.15)",
    color: "#f87171",
    border: "1px solid rgba(239, 68, 68, 0.3)",
  },
  info: {
    background: "rgba(59, 130, 246, 0.15)",
    color: "#60a5fa",
    border: "1px solid rgba(59, 130, 246, 0.3)",
  },
};

export default function Alert({
  children,
  variant = "info",
}) {
  const style = variants[variant] || variants.info;

  return (
    <div
      role={variant === "error" ? "alert" : "status"}
      style={{
        padding: "12px 16px",
        borderRadius: "8px",
        background: style.background,
        color: style.color,
        border: style.border,
        fontSize: "14px",
        fontWeight: "500",
        marginBottom: "16px",
      }}
    >
      {children}
    </div>
  );
}