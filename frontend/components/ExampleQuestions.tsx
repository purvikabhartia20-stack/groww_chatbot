// Pre-validated example questions — all factual, none advisory (EC-5.14)
const EXAMPLES = [
  "What is the expense ratio of HDFC Mid Cap Fund?",
  "What is the exit load for HDFC ELSS Tax Saver Fund?",
  "What is the lock-in period of HDFC ELSS Tax Saver Fund?",
];

interface Props {
  onSelect: (q: string) => void;
  disabled: boolean;
}

export default function ExampleQuestions({ onSelect, disabled }: Props) {
  return (
    <div className="px-4 pb-3">
      <p className="text-xs text-gray-400 dark:text-slate-500 mb-2 font-medium uppercase tracking-wide">
        Example questions
      </p>
      <div className="flex flex-col gap-1.5">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            disabled={disabled}
            className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-slate-800 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
