# Practitioner dashboard

A standalone view on top of the Second Draft agent. The practitioner opens one
page, sees their caseload, clicks a name, and gets that person's intake, goal,
and a running log of every session — Guava calls and human sessions together.
Opening a session shows the full note, so nothing has to be remembered between
appointments.

No build step, no dependencies, no backend. Two files.

## Open it

Double-click `index.html`, or serve the folder:

```bash
python -m http.server 8777 -d dashboard
```

Opening `index.html` straight off disk works too — `data.js` is loaded as a
classic script, not `fetch()`, so there is no CORS problem on `file://`.

## The data

**`data.js` is placeholder data.** Nothing in it is real. Joel Jussila is the
only populated record, with his own name at his own request; the other nine are
fictional people with no sessions, to show the empty state.

To swap in the real calls, replace `PATIENTS[0].sessions` with one object per
call:

```js
{ n: 7, date: "2026-08-29", channel: "ai", mode: "rehearsal", scene: "Alex",
  minutes: 19, flag: null,
  note: "Persona pushed harder. Went defensive twice.",
  detail: "Difficulty raised at his own request. Twice moved from stating his "
        + "need to defending his record...",
  followup: "Defensiveness appears when she implies he is being unfair." }
```

- `channel` — `"ai"` for a Guava call, `"human"` for a practitioner session
- `mode` — `coach` | `rehearsal` | `safety` | `ended`, matching `Mode` in
  `adaptive_models.py`
- `scene` — `SceneDefinition.counterpart_name`, or `null` outside roleplay
- `note` — one line, shown in the collapsed row
- `detail` — what actually happened, shown when the session is opened
- `followup` — what to pick up next time
- `flag` — `"safety"` marks an `on_escalate` exit and draws a red rule down the
  opened note; `"milestone"` marks a practitioner sign-off

Add a patient by appending to `PATIENTS`; an empty `sessions: []` renders the
empty state.

## Limits worth stating out loud

- **No authentication.** Anyone who opens the file or the URL sees everything.
  This is a demo prop, not a system of record. Do not put a real caller's name,
  number, or transcript in it.
- The session notes are written text, not generated summaries. If they are ever
  produced from real transcripts, say so on the page — a practitioner reading a
  note needs to know whether a person or a model wrote it.
