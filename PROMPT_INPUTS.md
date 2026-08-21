# Prompt Inputs

Verbatim log of the prompts that shaped this project (standing convention
across projects since 2026-07-15).

---

**2026-08-18** — initial direction-setting, in a conversation that started
with a general PACT/portfolio status check:

> Im not sure should we explore a new avenue but also related do some research on what things are starting to grow

Led to a research pass (Anthropic/Claude web research, not this repo) turning
up the EU AI Act's Aug 2, 2026 high-risk enforcement date as the strongest
candidate, given prior DO-330 tool-qualification and NIST AI RMF audit work
already done in this environment.

---

**2026-08-18** — confirming direction and asking about scope:

> ok should we go ahead with your recommended first one you will have to create a new platform for that one?

---

**2026-08-18** — the key design decision, switching from a scripted/API
approach to in-session assessment:

> why does this one need an API key can we do it without or something

> yeah lets switch to that and it can be integrated with you calude doing the check and making sure it comes back as passing and correct

This is the source of this project's central design constraint: no
`ANTHROPIC_API_KEY`, no scripted assessment — Claude reads each control
against real evidence in-session and writes the verdict directly, per
`README.md`'s "How assessment works" section.

---

**2026-08-18** — final go-ahead after reviewing the written plan
(`C:\Users\Yash Rao\.claude\plans\snug-plotting-lobster.md`):

> ok yeah go ahead

---

**2026-08-18** — after the first two-report version shipped, asked to combine
and elevate the presentation (this is what produced `dashboard.py`, replacing
the two-separate-files approach as the primary view):

> ok nice baseline now you can add real things to it like YRHUB we can make it dashboard and more in depth but it looks good as a combination

Follow-up loosening the format constraint mid-build:

> doesnt necessarily have to be a dashboard but a strong site or something you can do a remix of things like the hub

Feature-selection round (multi-select: all four picked, plus an open-ended
creative ask):

> Remediation tracker (Recommended), Filters, History/trend view, Export/print, We can also add additons like how yrhub has the stock ticker bar and globe moving we can add something to this one that relates I willl let you take over that

This is the direct source of the ticker bar (the "stock ticker" analog),
the remediation tracker (`remediation_log.json`), history plumbing
(`history.json`), and `export_pdf.py`.

---

**2026-08-18** — background/theme/performance round:

> ok nice now we can add more the background is just a blank one we can make it more impressive

> nice but slightly lagging now maybe reduce and you can add dark mode things and more additions

The lag report led to removing `background-attachment:fixed` (the actual
cause — layered gradients + fixed attachment force a scroll-frame repaint).
"dark mode things" is the source of the light/dark toggle; "more additions"
is the source of copy-link buttons.

---

**2026-08-18** — open-ended continuation, twice:

> lag is better and night and day is good and what else keep adding

> Keep going with whatever you think necessary

The second one is the standing permission this project is currently being
built under — search box, deep-link auto-open fix, sticky filter bar, print
button, then this doc-and-hygiene pass (dead-import cleanup, a real
accessibility fix on focus indicators, and bringing README.md back in sync
with what's actually shipped) all happened under that instruction rather
than a fresh ask each time.

---

**2026-08-18** — closing the actual open finding rather than adding more UI:

> go ahead keep going

(in response to being offered: resolve the EU-ART10 needs_human_review flag by
reading EU AI Act Article 3's definitions directly, rather than continuing to
add features.) Result: EU-ART10 moved Partial/Gap -> Met for both subjects,
with the reasoning recorded in both `findings/*.json` and
`remediation_log.json` (Open -> Resolved, full history kept) — the first real
find-through-resolve cycle the remediation tracker has actually completed.

---

**2026-08-18** — end of session, wrap-up:

> go ahjead and wrap and save it up and then we can submit to GIT tomorrow and we also need to fix up YRHUB making sure its good to put on linkedin and the public porfiles

Git init/commit deliberately deferred to tomorrow per this instruction — not
done tonight. YR Hub LinkedIn/public-profile readiness pass is queued as the
next piece of work, tracked outside this project.
