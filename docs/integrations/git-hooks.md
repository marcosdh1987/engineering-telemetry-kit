# Git hook integration

`engobs install` manages lightweight wrappers for:

- `post-commit`
- `post-checkout`

Behavior:

- preserves existing hook files
- appends only a clearly delimited managed block
- uses non-blocking commands such as `engobs snapshot --trigger commit || true`
- is idempotent across repeated installs
- removes only the managed block on uninstall
