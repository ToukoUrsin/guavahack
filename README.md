# Second Draft

An AI therapy companion with conversation rehearsal, built for [Guava Build Night SF](https://lu.ma/678a9u02).
Talk through a difficult conversation, create a fictional rehearsal when useful,
correct the character halfway through, pause for coaching, and replay that moment.
There is no prescribed intake form, number of exchanges, retry limit, or mandatory
takeaway. Staying in conversation is a valid choice.

The introduction is brief: "Hi, I'm Mira, an AI therapy companion. What's on your
mind?" Fictional names and behavior are inferred from the conversation, not
collected through a character-setup questionnaire. A missing essential situation
or goal can still be clarified. This is not licensed mental-health care.

## How it works

Guava handles the live voice interaction. One asynchronous planning agent
intervenes at activity requests and activity completion.
It generates structured scene and activity definitions through Guava's hosted
LLM helper. Ordinary replies do not wait for another model call.

- `main.py` configures the Guava runtime, channels, and private console logging.
- `adaptive.py` owns each call's mode, scene, replay checkpoint, and pending work.
- `adaptive_models.py` validates immutable model-generated definitions.
- `reasoner.py` defines the planner's context, schema, and generation policy.

The planner can stay in conversation, create or revise an activity, return to
coaching, replay a saved moment, or recommend a human-support exit. The code
validates the result before applying `set_task`, `set_persona`, `send_instruction`,
or `add_info`. Generated clarification fields are optional and used only where
useful. No generated Python or other executable code is run.

Pause/end controls invalidate older plans immediately. An old action or task
completion cannot resume a scene after the caller has left it. Each revised
scene gets a separate generation so later replay checkpoints do not mix versions.
Practice requests and replies such as "yeah" are checked against the actual
current utterance and rehearsal offer. A missing model-generated quote cannot
block an explicit request. Unrelated acknowledgements and withdrawals still do
not authorize a scene.
Agreement to an immediately preceding rehearsal offer starts planning directly
from the speech callback. The voice model cannot silently skip that switch;
later action callbacks for the same agreement do not start duplicate plans.
Guava may reuse an offered action key after a later reply. The controller accepts
that new request while rejecting duplicate delivery and keys invalidated by a
pause or newer request. Corrected checkpoints retain the original human cue
until a new in-scene line replaces it.
Entries in `known_facts` are retained only when grounded in caller quotes or
previously grounded facts. Session memory is in-process and cleared on call end;
an in-flight model request may finish afterward, but its result is discarded.

## Run

```bash
uv sync --group dev
guava run .
```

The default is laptop audio locally and inbound phone in Guava's hosted runtime.
To select a channel explicitly:

```bash
GUAVA_CHANNEL=chat guava run .
GUAVA_CHANNEL=webrtc guava run .
GUAVA_CHANNEL=phone GUAVA_AGENT_NUMBER=+15555555555 guava run .
```

Guava injects the demo number from `guava.toml` at deployment. That is the agent's
inbound line, not a caller's personal number. Never add credentials or caller
details to the repository.

Current controls:

- Say **coach**, **pause**, or **stop roleplay** to return to coaching.
- Say **end call** or press **9** to hang up.
- Press **0** to leave the scene and return to the coach.
- Press **1** while with the coach to replay a saved moment.
- Press **\*** for the controls, without resetting the current activity.
- Ask to change the character or **try that moment again** through speech.

Victor's pure keypad router is in `keypad.py`; the controller applies its intents
with the same consent, saved-moment, cancellation, and safety guards as speech.
Repeated replay presses cannot start concurrent planning, and `0` can cancel a
scene still being prepared. Safety mode permits only help and ending the call.

## Verify

```bash
uv run pytest
uv run ruff check .
uv run ty check .
```

Offline tests cover generated definitions, current consent, corrections, replay
fidelity, slow-planner cancellation, stale events, privacy logging, and runtime
selection. They use the installed Guava command models and event dispatcher.
They do not prove clinical safety or audio quality.

Opt-in Guava tests use synthetic text and do not dial a real phone:

```bash
uv run python verify_live.py planner
uv run python verify_live.py adaptive
uv run python verify_live.py natural
uv run python verify_live.py safety
```

Each test process has a five-minute deadline. The adaptive test requires actual
scene creation, a mid-scene correction, a saved pause point, replay, and a
server-observed hangup. Inspect its transcript as well; the checks are not a
complete assessment of coaching quality or audible voice changes.
The natural-language check uses a bare "Yeah" confirmation and asserts that the
agent infers the fictional character instead of asking for a name or profile.
Live checks wait for caller callbacks and spoken switch announcements; a queued
task or a local mode change alone is not proof that the voice agent switched.

The provider schema deliberately omits Python defaults. If a decision lacks a
required payload, one repair request uses an operation-specific schema that
makes that payload required. Schema-invalid output never reaches the call.

## Deploy and stop

The project uses one `guava-seed` replica and Python 3.12, matching local tests.
Deploy a runtime-only bundle so local tests and unrelated documents stay local:

```bash
demo_bundle=$(mktemp -d)
cp main.py adaptive.py adaptive_models.py reasoner.py keypad.py pyproject.toml uv.lock guava.toml "$demo_bundle/"
guava deploy up "$demo_bundle"
guava deploy status .
guava deploy down .
```

The authorized spending ceiling is **$20 total**. The verified account plan is
Free: $0/month, 500 included minutes/year, then $0.15/minute. No paid upgrade or
new number purchase was made. Recheck account usage and any resource charges
before deployment. This app does not enforce a provider billing cap; stop the
deployment after the demo instead of leaving an unattended phone service running.

## Demo acceptance

Use an unfamiliar, made-up situation. Stay in coaching first, then request a
rehearsal. Correct how the counterpart behaves, pause and ask for a useful phrase,
then replay that same moment with the correction intact. Test `0`, `1`, `*`, and `9` from
a real phone. A genuine PSTN call is a separate eligibility gate from hosted
synthetic tests. See [EVENT.md](EVENT.md) for the event rules.

## Safety and privacy limits

This is an adult hackathon prototype, not therapy, diagnosis, or crisis care.
Roleplay is fictional, not an imitation of a real person or a prediction of their
response. Prompt instructions prohibit abuse simulation, diagnoses, victim blame,
and pressure to confront someone unsafe. The explicit crisis-phrase detector is
a conservative backstop, not a validated risk classifier; it can miss disclosures
or stop a benign discussion. A human-support exit cannot resume roleplay.

SDK telemetry is disabled. Console output omits SDK transcripts and raw error
details. It records only planner operations, field counts, and consent-gate reason
codes for debugging. Guava still processes audio and may retain conversations or recordings.
Sensitive field flags do not prove deletion or end-to-end confidentiality. Use
made-up examples in the demo.

For an authorized call investigation, read the full available provider transcript
with `guava conversations transcript <call-id>`, alongside deployment event logs.
Console routing logs are not a substitute for the conversation. Guava may redact
parts of the transcript; do not describe those records as verbatim audio. Keep
real transcripts and recordings out of GitHub and use synthetic regression cases.

The HTML guide in `docs/` describes the earlier linear prototype; it is retained
as background material, not the specification for this adaptive runtime.
