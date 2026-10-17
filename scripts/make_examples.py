"""Run the example questions once through the real pipeline and cache the responses in
static/examples.json, so the demo can serve them with zero LLM cost.

  python scripts/make_examples.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from citesure.qa import QA  # noqa: E402

EXAMPLES = [
    "What minimum password length must verifiers require when a password is the only authentication factor?",
    "Can a service force users to include special characters and numbers in their passwords?",
    "What is Tier 1 of the CSF Tiers called?",
    "What is a CSF Community Profile?",
    "How much does a YubiKey 5 hardware authenticator cost?",
    "What must organizations do for each type of wireless access to a system before connections are established?",
]


def main() -> int:
    qa = QA()
    cached = []
    for q in EXAMPLES:
        r = qa.ask(q)
        cached.append({"question": q, "response": r.model_dump()})
        print(r.status, "|", q[:70], flush=True)
    out = ROOT / "static" / "examples.json"
    out.write_text(json.dumps({"cached": cached}, indent=1), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
