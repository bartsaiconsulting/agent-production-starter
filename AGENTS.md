# Repository Contribution Rules

## Git identity

- Every commit in this repository must use the repository-level identity `bartsai <dev@bartsaiconsulting.com>`.
- Before committing, verify `git config --local user.name` and `git config --local user.email`.
- Do not override the repository identity with command-scoped `git -c user.name=...` or `git -c user.email=...` values.

## Branch naming

- Name branches by change type and purpose, using prefixes such as `fix/`, `feature/`, or `docs/`.
- Do not use agent or tool identity prefixes such as `codex/`.
- Fetch the remote base before creating or merging a branch, and do not overwrite `main` history without explicit approval.
