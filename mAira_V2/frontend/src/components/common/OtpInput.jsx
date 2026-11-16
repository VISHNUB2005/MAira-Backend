import React, { useRef } from 'react';

export default function OtpInput({ value = ['', '', '', '', '', ''], onChange, autoFocus = true }) {
  const inputRefs = useRef([]);

  const handleChange = (index, e) => {
    const val = e.target.value;
    // Allow only numeric
    const cleanVal = val.replace(/\D/g, '');
    const newOtp = [...value];

    if (cleanVal.length > 1) {
      // Pasted multiple digits
      const digits = cleanVal.slice(0, 6).split('');
      for (let i = 0; i < 6; i++) {
        newOtp[i] = digits[i] || '';
      }
      onChange(newOtp);
      const nextIndex = Math.min(digits.length, 5);
      inputRefs.current[nextIndex]?.focus();
      return;
    }

    newOtp[index] = cleanVal ? cleanVal.slice(-1) : '';
    onChange(newOtp);

    // Auto advance to next input
    if (cleanVal && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !value[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pastedData) return;
    const newOtp = [...value];
    pastedData.split('').forEach((char, i) => {
      newOtp[i] = char;
    });
    onChange(newOtp);
    const nextIndex = Math.min(pastedData.length, 5);
    inputRefs.current[nextIndex]?.focus();
  };

  return (
    <div
      style={{
        display: 'flex',
        gap: '12px',
        justifyContent: 'space-between',
        width: '100%',
        margin: '12px 0',
      }}
      onPaste={handlePaste}
    >
      {Array.from({ length: 6 }).map((_, idx) => (
        <input
          key={idx}
          ref={(el) => (inputRefs.current[idx] = el)}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={value[idx] || ''}
          autoFocus={autoFocus && idx === 0}
          onChange={(e) => handleChange(idx, e)}
          onKeyDown={(e) => handleKeyDown(idx, e)}
          style={{
            width: '48px',
            height: '52px',
            borderRadius: '10px',
            background: 'rgba(13, 19, 34, 0.9)',
            border: value[idx]
              ? '1.5px solid #3B82F6'
              : '1.5px solid #1E293B',
            color: '#FFFFFF',
            fontSize: '1.35rem',
            fontWeight: 600,
            textAlign: 'center',
            outline: 'none',
            transition: 'all 0.15s ease',
            boxShadow: value[idx] ? '0 0 12px rgba(59, 130, 246, 0.25)' : 'none',
          }}
          onFocus={(e) => {
            e.target.style.borderColor = '#38BDF8';
            e.target.style.boxShadow = '0 0 12px rgba(56, 189, 248, 0.35)';
          }}
          onBlur={(e) => {
            e.target.style.borderColor = value[idx] ? '#3B82F6' : '#1E293B';
            e.target.style.boxShadow = value[idx] ? '0 0 12px rgba(59, 130, 246, 0.25)' : 'none';
          }}
        />
      ))}
    </div>
  );
}
