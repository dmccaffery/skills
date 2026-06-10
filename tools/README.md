# tools

Developer tooling for this repo:

- `eval/` — the three-tier eval harness (see the Evals section in the repo README).
- `go.mod` / `go.sum` — a standalone Go [tool module](https://go.dev/doc/modules/managing-dependencies#tools) that pins
  the Go developer CLIs, so their versions are tracked without leaking into the rest of the project. There is no Go
  application here — only `tool` directives.

## Pinned Go tools

| Tool                           | Purpose                                           |
| ------------------------------ | ------------------------------------------------- |
| `github.com/google/addlicense` | Add / verify license headers across source files. |

Run a pinned tool from anywhere in the repo via `go tool` against this module (or just use the Makefile targets):

```sh
go -C tools tool addlicense -l mit -c "Bitwise Media Group" -s=only -check .
```

## Maintenance

```sh
go -C tools get -tool <module/path>@latest   # add another tool
go -C tools get -tool -u ./...               # upgrade pinned tools
go -C tools mod tidy
```
