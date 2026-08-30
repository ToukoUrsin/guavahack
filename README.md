# Guava Build Night SF

> **Work-in-progress snapshot:** the fixed flow described below is being replaced
> by one asynchronous planning agent and dynamically generated activities.
> `adaptive.py`, `adaptive_models.py`, and `reasoner.py` contain the new runtime.
> The earlier `test_main.py` and `verify_live.py` harnesses still need migration.
> The new modules pass lint/type checks and six model-validation tests, but the
> full test suite is not yet green. The previous deployment has been stopped.

Hackathon workspace for the [Guava Voice AI Hackathon: Build Night SF](https://lu.ma/678a9u02).

This repo contains **Second Draft**, a voice agent for rehearsing difficult
conversations. It collects a de-identified scenario, changes persona for a short
roleplay, returns as a coach for one specific piece of feedback, and offers a
single do-over before closing with a takeaway.

Second Draft is deliberately a rehearsal coach, not a therapist. It does not
diagnose people, imitate a real person's voice, or claim to predict how someone
will respond. Explicit crisis language exits roleplay and directs the caller to
human support.

## Start here

1. Read [`EVENT.md`](EVENT.md) for the schedule, judging criteria, rules, and
   arrival checklist.
2. Run the focused tests:

   ```bash
   uv run python -m unittest -v
   ```

3. Start a local audio call:

   ```bash
   guava run .
   ```

The default channel is local audio on your laptop and inbound phone in Guava's
hosted runtime. Select a channel explicitly with `GUAVA_CHANNEL`:

```bash
GUAVA_CHANNEL=chat guava run .
GUAVA_CHANNEL=webrtc guava run .
GUAVA_CHANNEL=phone GUAVA_AGENT_NUMBER=+15555555555 guava run .
```

The phone channel requires `GUAVA_AGENT_NUMBER` in E.164 format. Guava injects
the demo line configured in `guava.toml` at deployment. That number is the
agent's inbound line, not a caller's personal number. Never add caller details
or credentials to this repository.

## Controls

- Say **coach** or **pause** to leave a scene. On a phone, press **0**.
- Say **end call** or press **9** to end the call.
- A consent refusal ends the session without starting a scene.
- A human-support exit cannot return to roleplay in the same session.

Victor owns the proposed `1 = retry` and `* = help` extension. Those controls
are not implemented here yet.

## Verification

```bash
uv sync --group dev
uv run python -m unittest -v
uv run ruff check main.py test_main.py verify_live.py
uv run ty check main.py test_main.py verify_live.py
```

The unit tests run without network access and use Guava's installed command
models and event dispatcher. They prove control wiring, not voice quality or
clinical safety.

Opt-in hosted tests use synthetic text through Guava, consume account minutes,
and do not dial a real phone:

```bash
uv run python verify_live.py full
uv run python verify_live.py safety
```

Each hosted test has a 150-second deadline. A passing run requires the expected
stages and a server-observed bot hangup. Review the generated transcript as well:
the automated checks do not grade the quality of coaching or verify audible
voice changes. Both paths passed on August 29, 2026. A genuine PSTN call remains
a separate hackathon eligibility check.

## Deployment and cost

The project uses one `guava-seed` replica and Python 3.12, matching the locally
tested Python version. Deploy only the runtime and dependency files; the
documentation and local tests are not runtime dependencies.

```bash
demo_bundle=$(mktemp -d)
cp main.py pyproject.toml uv.lock guava.toml "$demo_bundle/"
guava deploy up "$demo_bundle"
guava deploy status .
guava deploy down .
```

The approved account plan is Free: $0/month, 500 included minutes/year, then
$0.15/minute. No paid upgrade or new number purchase was made. The user's total
spending ceiling is $20. These prices are not an application-enforced spending
limit: check current usage and any resource charges, and stop the deployment
after the demo rather than leaving an unattended public phone agent running.

## Privacy and safety limits

This is an adult hackathon prototype, not treatment or crisis care. The explicit
phrase detector is a conservative backstop, not a validated clinical classifier;
it can miss disclosures or stop a benign discussion. Prompt instructions also
ask the agent to avoid abusive scenes, diagnoses, mind-reading, and victim blame.

SDK telemetry is disabled and console diagnostics omit SDK transcripts and raw
error details. The app adds no persistent conversation database. Guava still
processes the audio and may retain conversations/recordings; `sensitive=True`
on fields is not proof of deletion or end-to-end confidentiality. Use made-up
examples for the demo.

## Project files

- `main.py`: Second Draft agent and channel selection
- `test_main.py`: deterministic flow and safety-routing tests
- `verify_live.py`: bounded Guava-hosted synthetic conversation checks
- `guava.toml`: authenticated Guava project configuration
- `guava-docs.md`: Guava's coding-agent starter documentation snapshot
- `EVENT.md`: hackathon logistics, rules, and judging notes

## Useful links

- [Event on Luma](https://lu.ma/678a9u02)
- [Organizer setup guide](https://docs.google.com/document/d/1t7HvkXgFfhhLs69-HESnTfUlJfaQHHPtWM4m_4H1zE4/edit)
- [Guava quickstart](https://goguava.ai/docs/quickstart)
- [Guava agent documentation](https://goguava.ai/docs/agent)
