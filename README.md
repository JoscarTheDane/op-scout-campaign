# op-scout-campaign

An AI-operated business outreach campaign: automated lead discovery,
drafting, and email firing for a subsea/offshore consulting practice.
The operator is the Hermes Agent; the transport is the AgentMail API
(email dead-drop — no web infrastructure, no VPS).

## Architecture

```
Dawn Hunt cron (09:00)          Ledger cron (09:40)         Drafts cron (10:10)
─────────────────────           ─────────────────           ─────────────────
scrape job boards         →     reconcile tracker vs      →   draft in-doctrine
portal sweeps (Subsea 7,        AgentMail send log;         emails, max 3,
Saipem, ...)                       status board               NEVER sent
append raw leads           append-only fixes            awaiting owner's "fire"
```

The three crons are deliberately split — one long prompt made the
smaller model fail tool-call JSON parsing. Each cron has a narrow job
and a verifiable output file.

## Files

| File | Purpose |
|------|---------|
| `send_email.py` | The model-proof email sender: any agent, any model, can fire a campaign email. Reads the key from `AGENTMAIL_KEY` (never in the repo). Includes a **duplicate-fire guard** — before sending it checks the inbox send log for an identical (to, subject) pair and aborts unless `--force` |
| `.env.example` | Environment template — put your AgentMail key there, not in code |

## Operating doctrine (the interesting part)

- **The send log is the source of truth.** The lead tracker can lag;
  the AgentMail inbox send log cannot be argued with. Every dedup,
  every status board, every "have we emailed X?" answer goes through it.
- **Drafts are never auto-sent.** The pipeline stops at the draft. A
  human reviews; a human says fire.
- **Verification after every send.** A successful API call is not a
  successful email — the send log is re-read to confirm the `sent`
  label before anything is reported as done.
- **No-fabrication rule.** Capability bullets in drafts come from an
  approved list, never improvised; an invented credential in an
  application email is a career event, not a typo.

## Setup

```bash
pip install requests
export AGENTMAIL_KEY=***        # from https://app.agentmail.to
python send_email.py --to someone@company.com \
  --cc you@yourmail.com \
  --subject "..." --body-file body.txt [--attach cv.pdf]
```

## Licensing

MIT + [The Commons Clause](LICENSE) — free to use; if you make money
from it, share back.
