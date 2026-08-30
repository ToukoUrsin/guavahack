# Guava Build Night SF

Hackathon workspace for the [Guava Voice AI Hackathon: Build Night SF](https://lu.ma/678a9u02).

This repo starts from Guava's official inbound Python seed-agent scaffold. The
generated example in `main.py` runs a local voice call and demonstrates tasks,
fields, callbacks, RAG, and session handling.

## Start here

1. Read [`EVENT.md`](EVENT.md) for the schedule, judging criteria, rules, and
   arrival checklist.
2. Edit `main.py` once the product direction is selected.
3. Run the agent with:

   ```bash
   guava run .
   ```

The entrypoint currently uses `agent.call_local()`. Alternatives for an inbound
phone number, WebRTC, and terminal chat are documented at the bottom of
`main.py`.

## Project files

- `main.py`: generated Guava voice-agent starter
- `guava.toml`: authenticated Guava project configuration
- `guava-docs.md`: Guava's coding-agent starter documentation snapshot
- `EVENT.md`: hackathon logistics, rules, and judging notes

## Useful links

- [Event on Luma](https://lu.ma/678a9u02)
- [Organizer setup guide](https://docs.google.com/document/d/1t7HvkXgFfhhLs69-HESnTfUlJfaQHHPtWM4m_4H1zE4/edit)
- [Guava quickstart](https://goguava.ai/docs/quickstart)
- [Guava agent documentation](https://goguava.ai/docs/agent)
