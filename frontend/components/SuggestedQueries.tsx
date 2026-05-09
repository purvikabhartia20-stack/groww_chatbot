// Suggested query cards — spec: cards use rounded-lg (1rem), generous 24px padding
// Chips (dark mode) use rounded-full pill shape per spec
// Pre-validated factual queries only (EC-5.14)

interface Card {
  icon: React.ReactNode;
  label: string;
  query: string;
}

// Icons: 1.5px stroke, rounded terminals per design spec
function PercentIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
      <circle cx="9" cy="9" r="2" />
      <circle cx="15" cy="15" r="2" />
      <path d="M16 8L8 16" />
    </svg>
  );
}
function TimerIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="13" r="7" />
      <path d="M12 10v3l2 2" />
      <path d="M9 2h6M12 2v2" />
    </svg>
  );
}
function ExitIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 12h12M17 8l4 4-4 4" />
      <path d="M3 12V5a2 2 0 012-2h7" />
    </svg>
  );
}

const CARDS: Card[] = [
  {
    icon: <PercentIcon />,
    label: "What is the expense ratio of HDFC Mid Cap?",
    query: "What is the expense ratio of HDFC Mid Cap Fund?",
  },
  {
    icon: <TimerIcon />,
    label: "What is the lock-in for HDFC ELSS?",
    query: "What is the lock-in period of HDFC ELSS Tax Saver Fund?",
  },
  {
    icon: <ExitIcon />,
    label: "What is the exit load for HDFC ELSS?",
    query: "What is the exit load for HDFC ELSS Tax Saver Fund?",
  },
];

interface Props {
  onSelect: (q: string) => void;
  disabled: boolean;
}

export default function SuggestedQueries({ onSelect, disabled }: Props) {
  return (
    <div className="w-full max-w-2xl mx-auto px-4 md:px-12">
      {/* Label — label-sm: 12px/500/tracking */}
      <p className="text-center text-[12px] font-[500] tracking-[0.1em] uppercase text-[#6b7b72] dark:text-[#3c4a43] mb-4">
        Suggested Queries
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {CARDS.map((card) => (
          <button
            key={card.query}
            onClick={() => onSelect(card.query)}
            disabled={disabled}
            className="
              group text-left
              /* Card spec: rounded-lg (1rem), 1px border, 24px padding, ambient shadow */
              bg-[#ffffff] dark:bg-[#112218]
              border border-[#E8E8E8] dark:border-[#1a3a2a]
              rounded-[1rem] p-6
              shadow-[0px_4px_20px_rgba(0,0,0,0.04)]
              hover:border-[#00d09c] dark:hover:border-[#00d09c]
              hover:shadow-[0px_4px_20px_rgba(0,208,156,0.12)]
              transition-all duration-150
              disabled:opacity-40 disabled:cursor-not-allowed
            "
          >
            {/* Icon — on-surface-variant color */}
            <span className="block text-[#3c4a43] dark:text-[#bacac1] mb-3 group-hover:text-[#006c4f] dark:group-hover:text-[#00d09c] transition-colors">
              {card.icon}
            </span>
            {/* label-md: 14px/500 */}
            <span className="text-[14px] font-[500] leading-[20px] text-[#161d19] dark:text-[#eaf3ec]">
              {card.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
