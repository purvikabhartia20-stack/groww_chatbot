# Phase 5 — Edge Cases: Frontend Interface & Compliance Guardrails

## EC-5.1 — PII Regex Produces False Positives
**Scenario:** A valid query like "What is the SIP amount for plan 123456789012?" matches the Aadhaar regex (`\d{12}`) and gets blocked.  
**Risk:** Legitimate queries are rejected — user is falsely accused of sharing PII.  
**Handling:**
- Tighten PII regexes with context anchors:
  - Aadhaar: require surrounding whitespace or start/end of string — `(^|\s)\d{4}\s\d{4}\s\d{4}(\s|$)`
  - PAN: require word boundaries — `\b[A-Z]{5}[0-9]{4}[A-Z]\b`
  - Phone: require it to be a standalone token, not part of a longer number
- Maintain a regression test set of 15+ valid queries that must never be blocked by PII filters

---

## EC-5.2 — PII Regex Produces False Negatives (Misses Actual PII)
**Scenario:** User types their PAN as "A B C D E 1 2 3 4 F" (with spaces) — the regex doesn't match.  
**Risk:** PII reaches the backend query log (if any) or is embedded in the query sent to the LLM.  
**Handling:**
- Normalize input before PII scanning: collapse multiple spaces, remove common separators (`.`, `-`, `_`)
- Run PII scan on both raw and normalized versions of the input
- Add common obfuscation patterns to the regex set

---

## EC-5.3 — User Pastes a Very Long Block of Text as a Query
**Scenario:** User pastes a paragraph or a document excerpt into the chat input.  
**Risk:** Exceeds query length limit, or contains embedded PII, or overwhelms the classifier.  
**Handling:**
- Enforce 500-character limit in the UI input field (`maxlength` attribute on the input element)
- Show a character counter in the UI
- Backend also enforces the limit independently — never trust client-side validation alone

---

## EC-5.4 — Rapid Repeated Submissions (Accidental or Intentional Spam)
**Scenario:** User clicks "Send" multiple times quickly, or a script submits hundreds of queries per minute.  
**Risk:** OpenAI API costs spike; backend becomes slow or unresponsive.  
**Handling:**
- Client-side: disable the Send button while a response is in-flight
- Backend: implement per-session rate limiting — max 10 requests per minute per session token (anonymous, no login required)
- Return HTTP 429 with message: "Too many requests. Please wait a moment before asking again."

---

## EC-5.5 — Streamlit Session State Lost on Page Refresh
**Scenario:** User refreshes the browser — entire chat history disappears.  
**Risk:** User is confused or frustrated, especially mid-conversation.  
**Handling:**
- This is expected and intentional behavior (no session storage by design — privacy requirement)
- Display a clear notice on the welcome screen: "Chat history is not saved and will be cleared on refresh."
- Do not attempt to persist history to localStorage, cookies, or any server-side store

---

## EC-5.6 — FastAPI Backend Is Unreachable from the Streamlit Frontend
**Scenario:** Backend crashes or is not started — Streamlit UI sends a request and gets a connection error.  
**Risk:** Unhandled exception crashes the Streamlit app or shows a raw Python traceback to the user.  
**Handling:**
- Wrap all API calls in try/except in the Streamlit frontend
- On connection error → display: "The assistant is temporarily unavailable. Please try again shortly."
- Never expose raw error messages, stack traces, or internal URLs to the user

---

## EC-5.7 — Response Takes Too Long (LLM Latency Spike)
**Scenario:** OpenAI API response takes 15+ seconds due to load — user sees a frozen UI.  
**Risk:** User thinks the app is broken and submits the query again (causing duplicate requests).  
**Handling:**
- Show a loading spinner immediately after query submission
- Disable the input field and Send button while waiting
- Implement a client-side timeout: if no response in 30 seconds → show "Request timed out. Please try again."
- Backend timeout: set `httpx` or `requests` timeout to 25 seconds on the OpenAI call

---

## EC-5.8 — Disclaimer Banner Is Hidden or Dismissed
**Scenario:** A CSS bug or browser extension hides the "Facts-only. No investment advice." banner.  
**Risk:** User proceeds without seeing the compliance disclaimer.  
**Handling:**
- Disclaimer must be rendered as inline text in the chat area header, not just a floating overlay
- Use a sticky/fixed position element that cannot be scrolled past
- Include the disclaimer text in the first assistant message on every new session as well

---

## EC-5.9 — Refused Query Response Displayed with Error Styling
**Scenario:** Refusal responses are shown with a red background or warning icon — user interprets this as a system error.  
**Risk:** User loses trust or thinks the app is broken rather than understanding it's a policy boundary.  
**Handling:**
- Refused responses must use a neutral informational style (e.g., light grey background, info icon ℹ️)
- Never use red, orange, or warning-triangle styling for refusals
- Refusal message must be clearly worded as a scope boundary, not an error

---

## EC-5.10 — API Response Contains `refused: true` but Frontend Renders It as a Normal Answer
**Scenario:** A bug in the frontend ignores the `refused` flag and renders the refusal message in the same style as a factual answer, including a source citation.  
**Risk:** Refusal message appears to be a sourced factual answer — misleading.  
**Handling:**
- Frontend must explicitly check the `refused` field in every API response
- If `refused: true` → render in refusal style, do NOT render source URL as a citation
- Unit test: assert that a response with `refused: true` never renders a source citation link

---

## EC-5.11 — Source URL in Response Is Rendered as Plain Text Instead of a Hyperlink
**Scenario:** The `source_url` field is displayed as raw text — user cannot click through to verify.  
**Risk:** Source attribution is present but not actionable — reduces transparency.  
**Handling:**
- Always render `source_url` as a clickable hyperlink: `<a href="{source_url}" target="_blank">Source</a>`
- Open in a new tab (`target="_blank"`) so the user doesn't navigate away from the assistant
- Validate that `source_url` starts with `https://` before rendering as a link — never render `javascript:` or `data:` URIs

---

## EC-5.12 — User Submits an Empty Query
**Scenario:** User clicks Send with an empty or whitespace-only input field.  
**Risk:** Empty string reaches the backend — classifier and retriever behave unpredictably.  
**Handling:**
- Client-side: disable Send button if input is empty or whitespace-only
- Backend: validate that `query` field is non-empty after stripping whitespace — return HTTP 400 if empty
- Frontend shows inline message: "Please enter a question before submitting."

---

## EC-5.13 — CORS Error Blocks Frontend from Reaching Backend
**Scenario:** Streamlit frontend (port 8501) cannot reach FastAPI backend (port 8000) due to CORS policy.  
**Risk:** All queries fail silently or with a cryptic browser console error.  
**Handling:**
- Configure FastAPI with `CORSMiddleware` allowing the Streamlit origin explicitly
- In production, restrict CORS to the specific frontend domain — never use `allow_origins=["*"]` in production
- Document the required CORS configuration in `README.md`

---

## EC-5.14 — Example Questions in UI Lead to Refused Responses
**Scenario:** One of the three example questions shown in the UI (e.g., "Which HDFC fund is best for tax saving?") triggers the query classifier refusal.  
**Risk:** First interaction a user has with the assistant results in a refusal — poor first impression, erodes trust.  
**Handling:**
- All three example questions must be pre-validated against the classifier before deployment
- Example questions must be strictly factual: "What is the lock-in period of HDFC ELSS Tax Saver Fund?" not "Which fund is best for tax saving?"
- Re-validate example questions after any classifier rule update
