#!/usr/bin/env python3
"""
Generic email sender for Josh's campaign — model-proof.
Any AI agent (any model) can fire a campaign email with:

  python3 ~/client_campaign/send_email.py \
    --to info@company.com \
    --cc jsh.evan@gmail.com \
    --subject "..." \
    --body-file ~/client_campaign/body.txt \
    [--attach /path/to/file.pdf]

Defaults:
  - From: consultingsubsea@agentmail.to (business inbox)
  - CC: jsh.evan@gmail.com (Josh always sees everything)
  - Auth: key embedded below (boss key for consultingsubsea inbox)
"""
import argparse, base64, os, sys

# Key lives in the environment, never in the repo.
#   Linux/Termux:  export AGENTMAIL_KEY=***
#   Windows bash:  export AGENTMAIL_KEY=***
# See .env.example. The live key was removed before publication.
AM_TOKEN = os.environ.get("AGENTMAIL_KEY", "")
if not KEY:
    sys.exit("AGENTMAIL_KEY not set — export your AgentMail inbox-scoped key first.")
INBOX = "consultingsubsea@agentmail.to"
API = f"https://api.agentmail.to/inboxes/{INBOX}/messages/send"
DEFAULT_CV = "/data/data/com.termux/files/home/client_campaign/cv/Joshua_Evans_CV_3.4U.pdf"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--to", required=True)
    p.add_argument("--cc", default="jsh.evan@gmail.com")
    p.add_argument("--subject", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--attach", default=None, help="path to attachment (default: no attach)")
    p.add_argument("--attach-name", default=None)
    p.add_argument("--force", action="store_true", help="bypass duplicate-fire guard")
    args = p.parse_args()

    with open(args.body_file, "r", encoding="utf-8") as f:
        body = f.read()

    payload = {
        "to": args.to,
        "subject": args.subject,
        "text": body,
    }
    if args.cc:
        payload["cc"] = args.cc
    if args.attach:
        with open(args.attach, "rb") as f:
            payload["attachments"] = [{
                "filename": args.attach_name or os.path.basename(args.attach),
                "content_type": "application/pdf",
                "content": base64.b64encode(f.read()).decode(),
            }]

    import requests

    # ---- DUPLICATE-FIRE GUARD (added 2026-08-14 after a double-send) ----
    # Before sending, check the inbox send log for an identical (to, subject) pair.
    # If found, ABORT unless --force is given. Prevents the same email landing twice.
    list_url = f"https://api.agentmail.to/inboxes/{INBOX}/messages?limit=30"
    try:
        lr = requests.get(list_url, headers={"Authorization": "Bearer " + AM_TOKEN}, timeout=20)
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
    except Exception as e:
        print("GUARD CHECK FAILED (continuing):", e)

    r = requests.post(API, headers={"Authorization": "Bearer " + AM_TOKEN, "Content-Type": "application/json"},
                      json=payload, timeout=40)
    print("STATUS:", r.status_code)
    print("RESP:", r.text)
    if r.status_code != 200:
        sys.exit(1)

if __name__ == "__main__":
    main()
