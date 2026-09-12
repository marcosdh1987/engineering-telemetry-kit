# AI Gateway integration

`engobs` is backend-agnostic. When pointed at the current Engineering Gateway, it sends:

- `POST {ENGOBS_ENDPOINT}/events`
- `POST {ENGOBS_ENDPOINT}/ai-observations`

If `ENGOBS_API_KEY` is configured, requests include:

```text
Authorization: ******
```

The kit never depends on a fixed hostname, organization, IP, or LiteLLM credential.
