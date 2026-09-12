# Privacy model

`engobs` implements "measure the engineering process without observing the engineering content".

| Field / category | Collected? | Why | Privacy mode |
| --- | --- | --- | --- |
| Source code | NO | Explicitly forbidden | never |
| Diff / patch | NO | Explicitly forbidden | never |
| Filename / filepath | NO | Explicitly forbidden | never |
| Prompt / completion / transcript | NO | Explicitly forbidden | never |
| Developer name / email / username | NO | Explicitly forbidden | never |
| Remote URL | NO | Explicitly forbidden | never |
| Organization / project / repository | YES | Correlation and routing | standard; pseudonymized in strict |
| Branch | YES | Activity correlation | standard; pseudonymized in strict |
| Commit identifiers | YES | Delivery correlation | standard; pseudonymized in strict |
| Aggregate LOC counts | YES | Delivery / activity measurement | standard, strict |
| Verification outcome / duration | YES | Quality signal | standard, strict |
| AI tool name | YES | Tooling correlation | standard, strict |
| Opaque AI session id | YES | Session correlation | standard, strict |

## Precedence

Configuration precedence is:

```text
CLI args > ENV > repo config > global config > defaults
```

## Strict mode

Strict mode requires a local privacy salt. `engobs install` auto-generates and stores one in the global config when strict mode is selected and no salt exists. `engobs doctor` reports missing strict-mode salt as `ERROR`.

## Final privacy validation

Before sending any event, `engobs`:

1. builds a typed Pydantic event model (`extra = "forbid"`)
2. serializes the event
3. recursively validates forbidden fields
4. sends only if validation succeeds
