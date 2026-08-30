# Guava Voice AI Hackathon: Build Night SF

## Event

- Date: Saturday, August 29, 2026
- Doors: 5:30 PM
- Kickoff: 6:00 PM sharp
- Venue: House of AI, 40 Boardman Place, San Francisco, CA 94103
- Luma: https://lu.ma/678a9u02
- Organizer guide: https://docs.google.com/document/d/1t7HvkXgFfhhLs69-HESnTfUlJfaQHHPtWM4m_4H1zE4/edit
- Host: Guava, with Ankur Thakkar, AICamp admin, and Cooper Johnson
- Prize pool: up to $3,000
- Registration check: the live page displayed "You're In" and "My Ticket"
- Attendance check: 155 going when verified

Luma lists the event as 5:30–9:30 PM. The organizer guide has a longer detailed
schedule, with awards, networking, and an 11:00 PM hard stop. Plan around the
organizer guide.

## Schedule

| Time | Activity | Notes |
| --- | --- | --- |
| 5:30 PM | Doors and check-in | Bring photo ID, find a seat, plug in, food and bar open |
| 6:00 PM | Kickoff | Guava introduction, live agent build, rules and judging |
| 6:30 PM | Build session | Solo or teams of up to four; Guava engineers available |
| 7:00 PM | Dinner | Delivered to tables |
| 8:30 PM | Code freeze and table judging | 2-minute demo plus 1-minute Q&A; three judges per team |
| 9:30 PM | Top-five presentations | 3-minute demo plus 2-minute Q&A |
| 10:15 PM | Awards | First, second, and third place |
| 10:30 PM | Networking | Open networking |
| 11:00 PM | Hard stop | Event concludes |

## Eligibility and judging

The agent must place or answer at least one real call. A demo that never rings
is not eligible. Teams may have one to four people.

Judging criteria, in organizer-stated priority:

1. Functionality, heaviest weight
2. Technical complexity, heaviest weight
3. Creativity
4. Impact
5. User experience
6. Pitch and demo, lightest weight

## Bring

- Laptop and charger
- Wired headphones if available
- Phone for a real-call test
- Photo ID for check-in

## Installed starter

- Guava CLI: 0.40.0
- Scaffold: official `guava create` project
- Direction: inbound
- Runtime: `python-sandbox:3.14`
- Tier: `guava-seed`
- Entrypoint: `main.py`
- Package manager: uv

Run the starter from this directory:

```bash
guava run .
```

The generated entrypoint defaults to `agent.call_local()`. Before judging,
switch to or configure the path that satisfies the real-call rule, then verify
the actual phone call end to end.

## Submission

The Luma blast says to submit before the 8:30 PM code freeze. The pasted event
page exposed an "Open Google Form" action but not its underlying URL. Open the
live Luma event before the freeze to retrieve and verify the current form.
