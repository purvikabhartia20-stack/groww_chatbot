// Client-side PII detection — mirrors app/pii_filter.py
// Blocks queries before they even reach the backend (EC-5.1, EC-5.2)

const PII_PATTERNS: Record<string, RegExp> = {
  PAN: /\b[A-Z]{5}[0-9]{4}[A-Z]\b/,
  Aadhaar: /(^|\s)\d{4}[\s-]?\d{4}[\s-]?\d{4}(\s|$)/,
  Phone: /(^|\s)[6-9]\d{9}(\s|$)/,
  Email: /\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b/,
};

export function detectPII(text: string): string | null {
  // Normalize: collapse spaces
  const normalized = text.replace(/[ \t]+/g, " ").trim();
  for (const [type, pattern] of Object.entries(PII_PATTERNS)) {
    if (pattern.test(text) || pattern.test(normalized)) return type;
  }
  return null;
}
