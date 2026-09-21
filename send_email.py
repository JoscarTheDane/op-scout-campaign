#!/usr/bin/env python3
"""
Generic, model-proof campaign email sender.

Any AI agent, on any model, can fire a campaign email with:

  python3 send_email.py \\
    --to info@company.com \\
    --cc owner@example.com \\
    --subject "..." \\
    --body-file body.txt \\
    [--attach /path/to/CV.pdf]

Design notes
  - The key is read from the environment, never stored in the file. A sender that carries a
    credential is a credential leak waiting for a `git add -A`.
  - A duplicate-fire guard re-reads the inbox send log before sending and refuses an identical
    (to, subject) pair unless --force is given. It was added after a real double-send.
  - Exit codes: 0 sent · 1 send failed · 2 blocked as a duplicate.
"""
import argparse
import base64
import os
import sys

REQUESTS_HINT = "pip install requests"

INBOX = os.environ.get("AGENTMAIL_INBOX", "consultingsubsea@agentmail.to")
API = f"https://api.agentmail.to/inboxes/{INBOX}/messages/send"
LIST_API = f"https://api.agentmail.to/inboxes/{INBOX}/messages"

# Optional convenience: a default attachment path, used only to WARN when --attach is omitted.
CAMPAIGN_CV = os.environ.get("CAMPAIGN_CV", os.path.expanduser("~/campaign/cv/CV.pdf"))

AM_TOKEN = os.environ.get("AGENTMAIL_KEY", "")


def main():
    p = argparse.ArgumentParser(description="Send one campaign email via the AgentMail API.")
    p.add_argument("--to", required=True)
    p.add_argument("--cc", default=os.environ.get("CAMPAIGN_CC", ""),
                   help="always CC the owner so they see every outbound")
    p.add_argument("--subject", required=True)
    p.add_argument("--body-file", required=True,
                   help="file containing ONLY the body, starting at line 1 — no To:/Subject: headers")
    p.add_argument("--attach", default=None, help="path to an attachment (default: none)")
    p.add_argument("--attach-name", default=None, help="filename to present for the attachment")
    p.add_argument("--force", action="store_true",
                   help="bypass the duplicate-fire guard — only when a second send is intended")
    args = p.parse_args()

    if not AM_TOKEN:
        sys.exit("AGENTMAIL_KEY not set — export your AgentMail inbox-scoped key first (see .env.example).")

    try:
        import requests
    except ImportError:
        sys.exit(f"missing dependency: {REQUESTS_HINT}")

    with open(args.body_file, "r", encoding="utf-8") as f:
        body = f.read()

    # A body file that starts with headers means the draft was handed over untrimmed.
    for hdr in ("To:", "Subject:", "Cc:"):
        if body.lstrip().startswith(hdr):
            sys.exit(f"body file starts with '{hdr}' — strip the header lines; this tool sends the "
                     f"file verbatim and would put them in the message body.")

    payload = {"to": args.to, "subject": args.subject, "text": body}
    if args.cc:
        payload["cc"] = args.cc

    if args.attach:
        with open(args.attach, "rb") as f:
            payload["attachments"] = [{
                "filename": args.attach_name or os.path.basename(args.attach),
                "content_type": "application/pdf",
                "content": base64.b64encode(f.read()).decode(),
            }]
    elif os.path.exists(CAMPAIGN_CV):
        print(f"NOTE: no --attach given; a CV is available at {CAMPAIGN_CV} (not attached).")

    # ---- DUPLICATE-FIRE GUARD -------------------------------------------------
    # The send log is the source of truth. Check it before sending, not after.
    try:
        lr = requests.get(LIST_API, params={"limit": 30},
                          headers={"Authorization": "Bearer " + AM_TOKEN}, timeout=20)
        if lr.status_code == 200:
            existing = lr.json().get("messages", [])
            dup = [m for m in existing
                   if "sent" in (m.get("labels") or [])
                   and args.to in (m.get("to") or [])
                   and (m.get("subject") or "").strip().lower() == args.subject.strip().lower()]
            if dup and not args.force:
                print("DUPLICATE BLOCKED: identical send (to=%s, subj=%s) already logged at %s"
                      % (args.to, args.subject, dup[-1].get("timestamp", "?")))
                print("Re-run with --force only if you INTEND a second send.")
                sys.exit(2)
            if dup and args.force:
                print("WARNING: duplicate exists, proceeding due to --force")
        else:
            print(f"GUARD CHECK: unexpected status {lr.status_code} — continuing")
    except Exception as e:
        # Fail-open on the guard, fail-closed on the send. A network blip should not stop the
        # campaign, but the operator is told the guard did not run.
        print("GUARD CHECK FAILED (continuing):", e)

    r = requests.post(API,
                      headers={"Authorization": "Bearer " + AM_TOKEN,
                               "Content-Type": "application/json"},
                      json=payload, timeout=40)
    print("STATUS:", r.status_code)
    print("RESP:", r.text)
    if r.status_code != 200:
        sys.exit(1)


if __name__ == "__main__":
    main()
