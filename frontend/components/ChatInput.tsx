"use client";
import { useState, useRef, useEffect } from "react";

const MAX_CHARS = 500;

interface Props {
  onSubmit: (query: string) => void;
  disabled: boolean;
  placeholder?: string;
}

export default function ChatInput({ onSubmit, disabled, placeholder }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  }, [value]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const remaining = MAX_CHARS - value.length;
  const isOverLimit = remaining < 0;

  return (
    /* Input spec: rounded-lg (1rem), 1px border, focus → primary green border + 2px glow */
    <div className="
      w-full max-w-2xl mx-auto
      bg-[#ffffff] dark:bg-[#112218]
      border border-[#E8E8E8] dark:border-[#1a3a2a]
      rounded-[1rem]
      shadow-[0px_4px_20px_rgba(0,0,0,0.04)]
      px-5 pt-4 pb-3
      focus-within:border-[#00d09c]
      focus-within:shadow-[0_0_0_2px_rgba(0,208,156,0.2)]
      transition-all duration-150
    ">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value.slice(0, MAX_CHARS))}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder || "Ask about fund performance, risk, or details..."}
        rows={1}
        maxLength={MAX_CHARS}
        className="
          w-full resize-none bg-transparent
          text-[16px] leading-[24px] font-[400]
          text-[#161d19] dark:text-[#eaf3ec]
          placeholder-[#6b7b72] dark:placeholder-[#3c4a43]
          focus:outline-none
          disabled:cursor-not-allowed
        "
        aria-label="Ask a question about mutual fund schemes"
      />

      {/* Bottom row */}
      <div className="flex items-center justify-between mt-3">
        {/* Left: decorative icons (mic, image) — disabled, visual only */}
        <div className="flex items-center gap-3">
          <span className="text-[#bacac1] dark:text-[#3c4a43]" aria-hidden="true">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
              <path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" />
            </svg>
          </span>
          <span className="text-[#bacac1] dark:text-[#3c4a43]" aria-hidden="true">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <path d="M21 15l-5-5L5 21" />
            </svg>
          </span>
        </div>

        {/* Right: char counter + Ask button */}
        <div className="flex items-center gap-3">
          {value.length > 400 && (
            <span className={`text-[12px] font-[500] ${isOverLimit ? "text-[#ba1a1a]" : "text-[#6b7b72]"}`}>
              {remaining}
            </span>
          )}
          {/* Primary button: pill-shaped, #00d09c bg, white text */}
          <button
            onClick={handleSubmit}
            disabled={disabled || !value.trim() || isOverLimit}
            className="
              flex items-center gap-2
              bg-[#00d09c] hover:bg-[#00b888] active:bg-[#009e78]
              disabled:bg-[#bacac1] dark:disabled:bg-[#2A2A3E]
              disabled:cursor-not-allowed
              text-white disabled:text-[#6b7b72]
              text-[14px] font-[500] leading-[20px]
              px-5 py-2 rounded-full
              transition-colors duration-150
            "
            aria-label="Send question"
          >
            {disabled ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                <span>Asking...</span>
              </>
            ) : (
              <>
                <span>Ask</span>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
