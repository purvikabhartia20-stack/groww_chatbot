// Chat message bubbles — spec tokens applied
// User: primary-container (#00d09c) bg, white text
// Assistant: surface-container-lowest (#fff / #16213E) bg, 1px outline-variant border
// Refused/fallback: surface-container (#e8f0e9 / #1e2a3a), neutral info badge — never error red (EC-5.9)
// Source: secondary (#5367FF / #4f63fb) — spec: secondary used for links/citations
import type { Message } from "@/lib/api";

interface Props { message: Message; }

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="
          max-w-[75%] rounded-full px-5 py-3
          bg-[#00d09c] text-white
          text-[16px] leading-[24px] font-[400]
        ">
          {message.content}
        </div>
      </div>
    );
  }

  const isSpecial = message.refused || message.fallback || message.error;

  return (
    <div className="flex justify-start">
      <div className={`
        max-w-[80%] rounded-[1rem] px-5 py-4
        text-[16px] leading-[24px]
        shadow-[0px_4px_20px_rgba(0,0,0,0.04)]
        ${isSpecial
          ? "bg-[#e8f0e9] dark:bg-[#0d2218] border border-[#bacac1] dark:border-[#1a3a2a] text-[#3c4a43] dark:text-[#bacac1]"
          : "bg-[#ffffff] dark:bg-[#112218] border border-[#E8E8E8] dark:border-[#1a3a2a] text-[#161d19] dark:text-[#eaf3ec]"
        }
      `}>
        {/* Neutral info badge — never red (EC-5.9) */}
        {isSpecial && (
          <div className="flex items-center gap-1.5 mb-2 text-[#6b7b72] dark:text-[#3c4a43] text-[12px] font-[500]">
            <span aria-hidden="true">ℹ</span>
            <span>{message.refused ? "Outside scope" : "Not in indexed sources"}</span>
          </div>
        )}

        <p className="whitespace-pre-wrap">{message.content}</p>

        {/* Source — secondary color per spec, only valid corpus URLs (EC-5.11) */}
        {message.source_url && (
          <div className="mt-3 pt-3 border-t border-[#bacac1] dark:border-[#1a3a2a]">
            <a
              href={message.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[12px] font-[500] text-[#3247e2] dark:text-[#4f63fb] hover:underline break-all"
              aria-label="View source (opens in new tab)"
            >
              Source: {message.source_url}
            </a>
          </div>
        )}

        {message.last_updated && (
          <p className="mt-1 text-[12px] font-[500] text-[#6b7b72] dark:text-[#3c4a43]">
            Last updated from sources: {message.last_updated}
          </p>
        )}
      </div>
    </div>
  );
}
