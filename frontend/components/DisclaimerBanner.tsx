// Always-visible, non-dismissable compliance disclaimer (EC-5.8)
// Uses Groww tertiary/warning tokens — never error red
export default function DisclaimerBanner() {
  return (
    <div
      role="banner"
      aria-label="Compliance disclaimer"
      className="
        w-full sticky top-0 z-50
        bg-[#fff8e7] dark:bg-[#1a1200]
        border-b border-[#ffe082] dark:border-[#3d2800]
        px-4 py-2
        flex items-center justify-center gap-2
        text-xs font-medium text-[#7a5800] dark:text-[#ffd54f]
      "
    >
      <span className="text-sm" aria-hidden="true">⚠</span>
      <span>
        Facts-only. No investment advice. This assistant provides factual information about HDFC Mutual Fund schemes only.
      </span>
    </div>
  );
}
