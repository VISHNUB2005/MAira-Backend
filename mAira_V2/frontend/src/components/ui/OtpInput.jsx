import { useRef } from "react";

export default function OtpInput({
  value = "",
  onChange,
  length = 6,
  disabled = false,
}) {
  const refs = useRef([]);

  function handleChange(index, rawValue) {
    const digit = rawValue.replace(/\D/g, "").slice(-1);
    const chars = value.padEnd(length, " ").slice(0, length).split("");
    chars[index] = digit || " ";
    const next = chars.join("").trimEnd();

    onChange?.(next);

    if (digit && index < length - 1) {
      refs.current[index + 1]?.focus();
    }
  }

  function handleKeyDown(index, event) {
    if (event.key === "Backspace" && !value[index] && index > 0) {
      refs.current[index - 1]?.focus();
    }
  }

  return (
    <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
      {Array.from({ length }, (_, index) => {
        const char = value[index] || "";
        return (
          <input
            key={index}
            ref={(el) => (refs.current[index] = el)}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={char}
            disabled={disabled}
            onChange={(e) => handleChange(index, e.target.value)}
            onKeyDown={(e) => handleKeyDown(index, e)}
            style={{
              width: "48px",
              height: "56px",
              textAlign: "center",
              fontSize: "20px",
              fontWeight: "600",
              color: "#ffffff",
              background: "rgba(15, 23, 42, 0.6)",
              border: char
                ? "1px solid #3b82f6"
                : "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "8px",
              outline: "none",
              transition: "all 0.2s ease-in-out",
              boxShadow: char ? "0 0 10px rgba(59, 130, 246, 0.3)" : "none",
            }}
            onFocus={(e) => {
              e.target.style.borderColor = "#3b82f6";
              e.target.style.boxShadow = "0 0 12px rgba(59, 130, 246, 0.4)";
            }}
            onBlur={(e) => {
              if (!char) {
                e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                e.target.style.boxShadow = "none";
              }
            }}
          />
        );
      })}
    </div>
  );
}