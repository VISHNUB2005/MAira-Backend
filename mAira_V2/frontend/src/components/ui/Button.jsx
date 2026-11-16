export default function Button({
  children,
  type = "button",
  variant = "primary",
  disabled = false,
  onClick,
  className = "",
}) {
  const styles = {
    primary: {
      background: "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
      color: "#ffffff",
      border: "none",
      boxShadow: "0 4px 12px rgba(59, 130, 246, 0.3)",
    },
    secondary: {
      background: "rgba(255, 255, 255, 0.05)",
      color: "#ffffff",
      border: "1px solid rgba(255, 255, 255, 0.1)",
    },
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={className}
      style={{
        ...styles[variant],
        padding: "12px 20px",
        borderRadius: "8px",
        cursor: disabled ? "not-allowed" : "pointer",
        fontSize: "15px",
        fontWeight: "600",
        width: "100%",
        transition: "all 0.2s ease-in-out",
        opacity: disabled ? 0.6 : 1,
      }}
    >
      {children}
    </button>
  );
}