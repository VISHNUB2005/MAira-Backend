export default function Input({
  label,
  type = "text",
  value,
  onChange,
  placeholder = "",
  name,
  error,
  required = false,
  autoComplete,
}) {
  const id = name || label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div style={{ display: "grid", gap: "6px", marginBottom: "16px" }}>
      {label && (
        <label
          htmlFor={id}
          style={{
            fontWeight: "500",
            fontSize: "14px",
            color: "#e2e8f0",
          }}
        >
          {label} {required && <span style={{ color: "#ef4444" }}>*</span>}
        </label>
      )}
      <input
        id={id}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        autoComplete={autoComplete}
        aria-invalid={Boolean(error)}
        style={{
          width: "100%",
          padding: "12px 16px",
          background: "rgba(15, 23, 42, 0.6)",
          border: error ? "1px solid #ef4444" : "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: "8px",
          color: "#ffffff",
          fontSize: "15px",
          outline: "none",
          transition: "all 0.2s ease-in-out",
        }}
        onFocus={(e) => {
          if (!error) e.target.style.borderColor = "#3b82f6";
        }}
        onBlur={(e) => {
          if (!error) e.target.style.borderColor = "rgba(255, 255, 255, 0.1)";
        }}
      />
      {error && (
        <span style={{ fontSize: "13px", color: "#ef4444" }}>{error}</span>
      )}
    </div>
  );
}