"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { nanoid } from "nanoid";
import DisclaimerBanner from "@/components/DisclaimerBanner";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import SuggestedQueries from "@/components/SuggestedQueries";
import ThemeToggle from "@/components/ThemeToggle";
import { sendQuery, type Message } from "@/lib/api";
import { detectPII } from "@/lib/pii";

// Groww app icon — circle split blue top / green bottom by W-curve wave
// Used in header for both light and dark mode
function GrowwLogo() {
  return (
    <div className="w-9 h-9 rounded-full overflow-hidden flex-shrink-0">
      <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        {/* Blue top half */}
        <circle cx="18" cy="18" r="18" fill="#5367FF" />
        {/* Green bottom section — W-curve divider matching the Groww logo */}
        <path
          d="M0 22 C4 22 5 14 9 18 C11 20 13 24 18 20 C23 16 25 20 27 18 C31 14 32 22 36 22 L36 36 L0 36 Z"
          fill="#00D09C"
        />
      </svg>
    </div>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [piiError, setPiiError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleQuery = useCallback(async (query: string) => {
    setPiiError(null);

    const piiType = detectPII(query);
    if (piiType) {
      setPiiError(`Please do not share personal information (${piiType} detected).`);
      return;
    }

    const userMsg: Message = { id: nanoid(), role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const result = await sendQuery(query);
      setMessages((prev) => [
        ...prev,
        {
          id: nanoid(),
          role: "assistant",
          content: result.answer,
          source_url: result.source_url,
          last_updated: result.last_updated,
          refused: result.refused,
          fallback: result.fallback,
        },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      if (msg.toLowerCase().includes("personal information")) {
        setPiiError(msg);
        setMessages((prev) => prev.slice(0, -1));
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: nanoid(),
            role: "assistant",
            content: "The assistant is temporarily unavailable. Please try again in a moment.",
            error: true,
            fallback: true,
          },
        ]);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const isEmpty = messages.length === 0;

  return (
    <div className="page-bg flex flex-col min-h-screen transition-colors duration-200">

      {/* Dark mode ambient glow blobs — matches screenshot */}
      <div className="hidden dark:block fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[700px] h-[500px] rounded-full bg-[#00d09c]/8 blur-[160px]" />
        <div className="absolute bottom-0 right-0 w-[600px] h-[600px] rounded-full bg-[#0a2a1e]/80 blur-[100px]" />
        <div className="absolute top-1/3 -left-20 w-[350px] h-[350px] rounded-full bg-[#00d09c]/6 blur-[120px]" />
      </div>

      {/* Disclaimer */}
      <DisclaimerBanner />

      {/* Header — surface-container-lowest bg, outline-variant border */}
      <header className="
        relative z-10
        bg-[#ffffff]/80 dark:bg-transparent
        backdrop-blur-sm
        border-b border-[#bacac1]/40 dark:border-transparent
        px-6 py-3 flex items-center gap-3
      ">
        <GrowwLogo />
        {/* headline-md equivalent: 18px/500 */}
        <span className="flex-1 text-[18px] font-[500] leading-[28px] text-[#161d19] dark:text-[#eaf3ec]">
          Mutual Fund FAQ Assistant
        </span>
        <ThemeToggle />
      </header>

      {/* Main */}
      <main className="relative z-10 flex-1 flex flex-col">
        {isEmpty ? (
          /* ── Welcome state ── */
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-16 gap-8">

            {/* Heading — display-lg: 40px/700/-0.02em, scaled down on mobile */}
            <div className="text-center max-w-xl px-4">
              <h1 className="text-[32px] md:text-[40px] font-[700] leading-[40px] md:leading-[48px] tracking-[-0.02em] text-[#161d19] dark:text-[#eaf3ec] mb-4">
                How can I help with{" "}
                <span className="text-[#006c4f] dark:text-[#00d09c]">HDFC Funds</span>?
              </h1>
              {/* body-lg: 18px/400/28px */}
              <p className="text-[18px] font-[400] leading-[28px] text-[#3c4a43] dark:text-[#bacac1]">
                Access factual, source-backed insights on performance, allocation,
                and risk metrics directly from official scheme documents.
              </p>
            </div>

            {/* Suggested queries */}
            <SuggestedQueries onSelect={handleQuery} disabled={loading} />
          </div>
        ) : (
          /* ── Chat state ── */
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 max-w-2xl w-full mx-auto">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {/* Typing indicator — primary-container dots */}
            {loading && (
              <div className="flex justify-start">
                <div className="
                  bg-[#ffffff] dark:bg-[#112218]
                  border border-[#E8E8E8] dark:border-[#1a3a2a]
                  rounded-[1rem] px-5 py-4
                  shadow-[0px_4px_20px_rgba(0,0,0,0.04)]
                ">
                  <div className="flex gap-1.5 items-center h-5">
                    {["0s", "0.15s", "0.3s"].map((delay) => (
                      <span
                        key={delay}
                        className="w-2 h-2 bg-[#00d09c] rounded-full animate-bounce"
                        style={{ animationDelay: delay }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}

        {/* PII error — tertiary warning tokens, never error red */}
        {piiError && (
          <div className="relative z-10 mx-auto w-full max-w-2xl px-4 mb-2">
            <div className="
              px-4 py-3 rounded-[1rem]
              bg-[#fff8e7] dark:bg-[#1a1200]
              border border-[#ffe082] dark:border-[#3d2800]
              text-[14px] font-[500] text-[#7a5800] dark:text-[#ffd54f]
              flex items-center gap-2
            ">
              <span aria-hidden="true">🔒</span>
              <span>{piiError}</span>
              <button
                onClick={() => setPiiError(null)}
                className="ml-auto opacity-60 hover:opacity-100 transition-opacity"
                aria-label="Dismiss"
              >✕</button>
            </div>
          </div>
        )}

        {/* Input — spacing: lg (24px) from content, container-margin */}
        <div className="relative z-10 w-full px-4 md:px-12 pb-6 pt-3">
          <ChatInput
            onSubmit={handleQuery}
            disabled={loading}
            placeholder={isEmpty
              ? "Ask about fund performance, risk, or details..."
              : "Ask about a mutual fund scheme..."}
          />
          {/* Footer — label-sm: 12px/500, outline color */}
          <p className="text-center text-[12px] font-[500] tracking-[0.08em] uppercase text-[#6b7b72] dark:text-[#3c4a43] mt-4">
            © Always consult a financial advisor before investing.
          </p>
        </div>
      </main>
    </div>
  );
}
