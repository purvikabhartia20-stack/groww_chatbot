// API client for the FastAPI backend

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface QueryResponse {
  answer: string;
  source_url: string | null;
  last_updated: string | null;
  refused: boolean;
  fallback: boolean;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  source_url?: string | null;
  last_updated?: string | null;
  refused?: boolean;
  fallback?: boolean;
  error?: boolean;
}

export async function sendQuery(query: string): Promise<QueryResponse> {
  const res = await fetch(`${API_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail || `Request failed (${res.status})`);
  }

  return res.json();
}
