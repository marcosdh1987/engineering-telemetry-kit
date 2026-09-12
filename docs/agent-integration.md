# Agent integration

Future AI skills should treat `engobs` as an external reusable dependency, not as code duplicated into templates.

Recommended bootstrap steps:

```bash
engobs install
engobs doctor
```

Recommendations:

- prefer a preinstalled `engobs` binary on developer machines or runners
- select environment-specific behavior through profiles
- never pass prompts, transcripts, or source content to `engobs`
- keep hooks non-blocking (`|| true`) so telemetry never blocks engineering work
