# Security & Privacy

Implemented in this slice:

- **Untrusted input.** Uploaded files and pasted text are treated as data, never
  instructions. Document macros/scripts are never executed; URLs in content are never
  auto-fetched.
- **Prompt-injection resistance.** The Qwen system prompt instructs the model to treat
  source text strictly as data to extract from. Crucially, model output cannot control
  calendar serialization — deterministic code does that, and every field is validated.
- **File validation.** Extension + content magic sniffing; corrupt files are rejected
  with a clear error; size limits (`MAX_UPLOAD_BYTES`).
- **Artifact safety.** Random 32-hex ids, filename sanitization (`os.path.basename` +
  allowlist), path-traversal guard (id must match `[0-9a-f]{32}`), TTL expiry + cleanup.
- **Credential isolation.** Qwen credentials live only in backend env; never sent to
  the frontend.
- **Request limits & deadlines.** Bounded request sizes; explicit gRPC deadlines;
  bounded, provider-side retries (no retries on deterministic validation errors).
- **Logging hygiene.** Structured logs exclude raw email/document bodies and secrets.
- **Disclosure.** When `QWEN_PROVIDER=openai_compatible`, content is sent to the
  configured Qwen server — document this for your users per your privacy policy.

Not yet implemented (roadmap — do not assume these are in place):

- TLS termination (configure at your ingress/proxy for production; use secure gRPC
  channels when services cross trust boundaries).
- User authentication/authorization and per-user artifact ownership (the MVP is
  stateless with short-lived anonymous artifacts).
- Distributed rate limiting (add Redis-backed limiting at the gateway).
