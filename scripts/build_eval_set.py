"""Build eval/questions.jsonl from the drafted items below and VERIFY every gold passage.

The 50 questions were drafted by an LLM (Claude) reading the ingested corpus. Verification here is
programmatic, not human: each gold passage must occur verbatim (whitespace/quote-normalised) in the
text extracted from the stated document, and the PDF page is derived from where it occurs.
Every item is written with "verified_by_human": false. A human should review before client use.

  python scripts/build_eval_set.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from citesure.answer.verify import norm_chars  # noqa: E402
from citesure.ingest.index import Index  # noqa: E402

TOK = re.compile(r"\w+")

# (category, question, gold_answer, [(doc_id, passage), ...])  -- unanswerable: sources = []
A = [
    # ---- facts (12)
    ("fact", "What minimum password length must verifiers require when a password is the only authentication factor, and what is the minimum when it is used in multi-factor authentication?",
     "15 characters for single-factor passwords; 8 characters when only used as part of multi-factor authentication.",
     [("sp800-63b-4", "authentication mechanism to be a minimum of 15 characters in length. Verifiers and CSPs MAY allow passwords that are only used as part of multi-factor authentication processes to be shorter but SHALL require them to be a minimum of eight characters in length.")]),
    ("fact", "What kind of cryptographic authenticator does AAL3 require?",
     "A cryptographic authenticator with a non-exportable private key that provides phishing resistance.",
     [("sp800-63b-4", "AAL3 authentication requires the use of a cryptographic authenticator with a non-exportable private key that provides phishing resistance.")]),
    ("fact", "Is an inactivity timeout required at AAL1?",
     "No. An inactivity timeout may be applied but is not required at AAL1.",
     [("sp800-63b-4", "An inactivity timeout MAY be applied but is not required at AAL1.")]),
    ("fact", "How many digits must an issued account recovery code include at minimum?",
     "At least six decimal digits (or equivalent) from an approved random bit generator.",
     [("sp800-63b-4", "The issued recovery code SHALL include at least six decimal digits (or equivalent) from an approved random bit generator")]),
    ("fact", "May an authenticated session fall back to an insecure transport such as http after authentication?",
     "No. Authenticated sessions shall not fall back to an insecure transport (e.g., from https to http).",
     [("sp800-63b-4", "authenticated sessions SHALL NOT fall back to an insecure transport (e.g., from https to http).")]),
    ("fact", "Must a verifier check the entire submitted password or may it truncate it?",
     "It must request the password in full and verify the entire submitted password without truncating it.",
     [("sp800-63b-4", "Verifiers SHALL request the password to be provided in full (not a subset of it) and SHALL verify the entire submitted password (e.g., not truncate it).")]),
    ("fact", "What must organizations do for each type of wireless access to a system before connections are established?",
     "Authorize each type of wireless access prior to establishing such connections.",
     [("sp800-171r3", "Authorize each type of wireless access to the system prior to establishing such connections.")]),
    ("fact", "What are examples of audit logging process failures?",
     "Software and hardware errors, failures in audit log capturing mechanisms, and reaching or exceeding audit log storage capacity.",
     [("sp800-171r3", "Audit logging process failures include software and hardware errors, failures in audit log capturing mechanisms, and reaching or exceeding audit log storage capacity.")]),
    ("fact", "What kinds of media use does the system media use restriction requirement limit or prohibit?",
     "The use of certain types of media, such as external hard drives, flash drives, or smart displays.",
     [("sp800-171r3", "this requirement restricts or prohibits the use of certain types of media, such as external hard drives, flash drives, or smart displays.")]),
    ("fact", "Give an example of a third party that may take a primary role in incident response.",
     "A managed security service provider (MSSP) performing incident detection, response, and recovery activities.",
     [("sp800-61r3", "Some third parties may fill a primary role (e.g., an MSSP performing incident detection, response, and recovery activities)")]),
    ("fact", "What is the purpose of SP 800-61 Revision 3?",
     "To help organizations incorporate cybersecurity incident response recommendations and considerations throughout their cybersecurity risk management activities.",
     [("sp800-61r3", "This publication seeks to help organizations incorporate cybersecurity incident response recommendations and considerations throughout their cybersecurity risk management activities.")]),
    ("fact", "What do CSF Quick-Start Guides provide?",
     "Actionable guidance on using the CSF and its online resources.",
     [("csf-2.0", "Quick-Start Guides that give actionable guidance on using the CSF and its online resources")]),
    # ---- definitions (8)
    ("definition", "How does SP 800-171r3 define multi-factor authentication?",
     "Authentication requiring two or more different factors: something you know, something you have, or something you are.",
     [("sp800-171r3", "Multi-factor authentication requires the use of two or more different factors to achieve authentication.")]),
    ("definition", "What does separation of duties address?",
     "The potential for abuse of authorized privileges, reducing the risk of malevolent activity without collusion.",
     [("sp800-171r3", "Separation of duties addresses the potential for abuse of authorized privileges and reduces the risk of malevolent activity without collusion.")]),
    ("definition", "How is a mobile device defined in SP 800-171r3?",
     "A computing device with a small form factor that can be carried by a single individual and operates without a physical connection.",
     [("sp800-171r3", "A mobile device is a computing device with a small form factor such that it can be carried by a single individual")]),
    ("definition", "What is a CSF Community Profile?",
     "A baseline of CSF outcomes created and published to address shared interests and goals among a number of organizations, typically for a sector, technology, threat type or other use case.",
     [("csf-2.0", "A Community Profile is typically developed for a particular sector, subsector, technology, threat type, or other use case.")]),
    ("definition", "What is a nonce according to SP 800-63B-4?",
     "A value used in security protocols that is never repeated with the same key.",
     [("sp800-63b-4", "nonce A value used in security protocols that is never repeated with the same key.")]),
    ("definition", "What is a passphrase?",
     "A password consisting of a sequence of words or other text that a claimant uses to authenticate their identity.",
     [("sp800-63b-4", "A password that consists of a sequence of words or other text that a claimant uses to authenticate their identity.")]),
    ("definition", "What is pharming?",
     "An attack in which an attacker causes the subscriber to be redirected to a fraudulent website.",
     [("sp800-63b-4", "pharming An attack in which an attacker causes the subscriber to be redirected to a fraudulent website")]),
    ("definition", "What do the CSF Tiers characterize?",
     "The rigor of an organization's cybersecurity risk governance and management practices.",
     [("csf-2.0", "Tiers characterize the rigor of an organization")]),
    # ---- tables (6)
    ("table", "What is the CSF Category Identifier for Cybersecurity Supply Chain Risk Management?",
     "GV.SC", [("csf-2.0", "Cybersecurity Supply Chain Risk Management | GV.SC")]),
    ("table", "What is the CSF Category Identifier for Asset Management?",
     "ID.AM", [("csf-2.0", "Asset Management | ID.AM")]),
    ("table", "What is Tier 1 of the CSF Tiers called?",
     "Tier 1 is Partial.", [("csf-2.0", "Tier 1: Partial | Application of the organizational cybersecurity risk strategy is managed in an ad hoc manner.")]),
    ("table", "What is Tier 4 of the CSF Tiers called?",
     "Tier 4 is Adaptive.", [("csf-2.0", "Tier 4: Adaptive | There is an organization-wide approach to managing cybersecurity risks")]),
    ("table", "Which CSF 2.0 Function corresponds to the Detection and Analysis phase of the previous incident response life cycle model?",
     "Detect (plus the Improvement Category of Identify).", [("sp800-61r3", "Detection & Analysis | Detect")]),
    ("table", "Which CSF 2.0 Functions correspond to the Containment, Eradication and Recovery phase of the previous incident response life cycle model?",
     "Respond and Recover.", [("sp800-61r3", "Containment, Eradication & Recovery | Respond")]),
    # ---- paraphrase (6)
    ("paraphrase", "Can a service force users to include special characters and numbers in their passwords?",
     "No. Other composition requirements for passwords shall not be imposed.",
     [("sp800-63b-4", "Other composition requirements for passwords SHALL NOT be imposed.")]),
    ("paraphrase", "What is the weakest point in many authentication systems when a user has lost their authenticators?",
     "The process followed when a subscriber loses control of authenticators and needs to replace them (recovery).",
     [("sp800-63b-4", "The weak point in many authentication mechanisms is the process followed when a subscriber loses control of one or more authenticators and needs to replace them.")]),
    ("paraphrase", "Why should out-of-support software be replaced?",
     "Vendors no longer provide critical patches or updates, which gives adversaries opportunities to exploit weaknesses.",
     [("sp800-171r3", "An example of unsupported components includes when vendors no longer provide critical software patches or product updates")]),
    ("paraphrase", "What counts as organizational property that leavers must return, according to the personnel security requirement?",
     "Hardware authentication tokens, administration manuals, keys, identification cards and building passes.",
     [("sp800-171r3", "Security-related system property includes hardware authentication tokens, system administration technical manuals, keys, identification cards, and building passes.")]),
    ("paraphrase", "Is the CSF Core a to-do list I should work through item by item?",
     "No. The outcomes are not a checklist of actions to perform; actions vary by organization and use case.",
     [("csf-2.0", "These outcomes are not a checklist of actions to perform; specific actions taken to achieve an outcome will vary by organization and use case")]),
    ("paraphrase", "What are the two kinds of session timeout described for reauthentication?",
     "An overall timeout limiting session duration after authentication, and an inactivity timeout ending a session without subscriber activity.",
     [("sp800-63b-4", "An overall timeout limits the duration of an authenticated session to a specified period following authentication or a previous reauthentication.")]),
    # ---- multi-hop within a document (4)
    ("multi-hop", "What length must single-factor passwords have, and may a service impose other composition rules?",
     "At least 15 characters, and no other composition requirements may be imposed.",
     [("sp800-63b-4", "authentication mechanism to be a minimum of 15 characters in length."),
      ("sp800-63b-4", "Other composition requirements for passwords SHALL NOT be imposed.")]),
    ("multi-hop", "What does SP 800-171r3 require to authorize wireless access, and how must wireless access be protected?",
     "Authorize each type of wireless access before connection; protect wireless access using authentication and encryption.",
     [("sp800-171r3", "Authorize each type of wireless access to the system prior to establishing such connections."),
      ("sp800-171r3", "Protect wireless access to the system using authentication and encryption.")]),
    ("multi-hop", "What are CSF Organizational Profiles used for and what do Tiers do?",
     "Profiles describe current and/or target posture and are used to understand, tailor, assess, prioritize and communicate the Core outcomes; Tiers characterize the rigor of risk governance and management practices.",
     [("csf-2.0", "Organizational Profiles are used to understand, tailor, assess, prioritize, and communicate the"),
      ("csf-2.0", "Tiers characterize the rigor of an organization")]),
    ("multi-hop", "What does SP 800-61r3 say about its purpose and the common language it provides?",
     "It helps organizations incorporate incident response into cybersecurity risk management and provides a common language to communicate internally and externally about incident response plans and activities.",
     [("sp800-61r3", "This publication seeks to help organizations incorporate cybersecurity incident response recommendations"),
      ("sp800-61r3", "It also provides a common language that all organizations can use to communicate internally and externally regarding their incident response plans and activities.")]),
    # ---- cross-document (4)
    ("cross-document", "How does SP 800-171r3 define multi-factor authentication, and what minimum length does SP 800-63B-4 set for passwords used only as part of multi-factor authentication?",
     "Two or more different factors; passwords used only in multi-factor authentication must be at least eight characters.",
     [("sp800-171r3", "Multi-factor authentication requires the use of two or more different factors to achieve authentication."),
      ("sp800-63b-4", "SHALL require them to be a minimum of eight characters in length.")]),
    ("cross-document", "Which CSF Functions help prevent and prepare for incidents, and how does SP 800-61r3 base its incident response life cycle on the CSF?",
     "Govern, Identify and Protect help prevent and prepare; SP 800-61r3 proposes a life cycle model based on CSF 2.0 Functions.",
     [("csf-2.0", "outcomes help prevent and prepare for incidents"),
      ("sp800-61r3", "proposes a new life cycle model based on CSF 2.0 Functions")]),
    ("cross-document", "How do SP 800-171r3 and SP 800-63B-4 each treat ending sessions or timeouts?",
     "SP 800-171r3: terminating network connections associated with sessions includes deallocating addresses or port pairs; SP 800-63B-4 describes overall and inactivity timeouts (inactivity timeout not required at AAL1).",
     [("sp800-171r3", "Terminating network connections associated with communications sessions includes deallocating TCP/IP addresses or port pairs at the operating system level"),
      ("sp800-63b-4", "An inactivity timeout terminates a session that has not had activity from the subscriber for a specified period.")]),
    ("cross-document", "How do the CSF and SP 800-171r3 each address supply chain risk?",
     "The CSF can foster risk oversight and communication across supply chains; SP 800-171r3 notes dependence on external providers increases risk (counterfeits, tampering, malicious software).",
     [("csf-2.0", "Supply chain risks: An organization can use the CSF to foster cybersecurity risk oversight and communications with stakeholders across supply chains."),
      ("sp800-171r3", "Dependence on the products, systems, and services of external providers and the nature of the relationships with those providers present an increasing level of risk")]),
]

# on-topic questions the corpus does not answer (checked below against the corpus with keyword guards)
U = [
    ("How much does a SOC 2 audit cost for a CUI contractor?", ["soc 2", "soc2"]),
    ("What financial penalty applies to a contractor that fails to implement SP 800-171 requirements?", ["penalty", "financial penalt"]),
    ("How much does a YubiKey 5 hardware authenticator cost?", ["yubikey"]),
    ("What hourly rate do MSSPs charge for incident response retainers?", ["hourly rate", "retainer"]),
    ("How many US organizations reported a ransomware incident in 2023?", ["2023 ransomware"]),
    ("What GDPR fines apply when a data breach is reported late?", ["gdpr"]),
    ("Which Linux distribution does NIST recommend for hosting a CUI system?", ["linux", "ubuntu"]),
    ("Which CSF tier has the Department of Defense been assigned?", ["department of defense has"]),
    ("How many analysts must a security operations center employ according to SP 800-61r3?", ["analysts must"]),
    ("What is the CMMC Level 2 assessment cost for a small business?", ["cmmc"]),
]


def locate(index: Index, doc_id: str, passage: str):
    """Find passage (token-normalised) in a chunk of doc_id. Returns (chunk, page) or None."""
    gt = [t.lower() for t in TOK.findall(norm_chars(passage))]
    for cid in index.order:
        ch = index.chunks[cid]
        if ch.doc_id != doc_id:
            continue
        spans = [(m.group().lower(), m.start()) for m in TOK.finditer(norm_chars(ch.text))]
        toks = [s[0] for s in spans]
        for i in range(len(toks) - len(gt) + 1):
            if toks[i : i + len(gt)] == gt:
                return ch, ch.page_for_offset(spans[i][1])
    return None


def main() -> int:
    index = Index()
    corpus_lc = " ".join(c.text.lower() for c in index.chunks.values())
    items, bad = [], []
    for n, (cat, q, gold, sources) in enumerate(A):
        gs = []
        for doc_id, passage in sources:
            hit = locate(index, doc_id, passage)
            if not hit:
                bad.append((n, doc_id, passage[:70]))
                continue
            gs.append({"doc_id": doc_id, "page": hit[1], "passage": passage})
        items.append({"category": cat, "question": q, "answerable": True, "gold_answer": gold, "gold_sources": gs})
    for q, guards in U:
        for g in guards:
            if g in corpus_lc:
                bad.append(("unanswerable", q, f"corpus mentions {g!r}"))
        items.append({"category": "unanswerable", "question": q, "answerable": False,
                      "gold_answer": "DECLINE", "gold_sources": []})
    if bad:
        for b in bad:
            print("VERIFY FAILED:", b)
        return 1

    ans_i = un_i = 0
    out = []
    for k, it in enumerate(items, 1):
        if it["answerable"]:
            dev = ans_i % 3 == 1
            ans_i += 1
        else:
            dev = un_i in (0, 4, 8)
            un_i += 1
        out.append({"id": f"q{k:03d}", **it, "split": "dev" if dev else "test", "verified_by_human": False})
    path = ROOT / "eval" / "questions.jsonl"
    path.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n", encoding="utf-8")
    from collections import Counter

    print(f"wrote {len(out)} questions -> {path}")
    print(Counter(o["category"] for o in out), Counter(o["split"] for o in out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
