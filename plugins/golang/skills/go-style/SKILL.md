---
name: go-style
description: Modern Go code style for stdlib-first programs — error wrapping with %w, sentinel errors, structured logging with log/slog, context threading, consumer-defined interfaces, nil-safe constructors, net/http servers with method-pattern routing, flag/env configuration for services, and cobra commands with viper configuration for CLI tools. Use when writing, reviewing, or refactoring Go code (.go files, packages, services), adding error handling or logging to a Go program, building a Go CLI tool or subcommands (cobra, viper), or deciding how to shape interfaces, constructors, configuration, or HTTP handlers in Go.
license: MIT
---

# Go style conventions

Stdlib-first conventions for modern Go (1.22+). Apply them to new code and match them when editing
existing code; reach for a third-party dependency only when the standard library genuinely cannot
do the job. For the rationale behind each rule and extended examples, see
[reference.md](reference.md).

## 1. Wrap errors with `%w` and the failing operation, exactly once

Name the operation lowercase, no "failed to", no trailing punctuation. Wrap where context is
added; pass through errors that are already contextual:

```go
if err := v.BindPFlags(fs); err != nil {
	return nil, fmt.Errorf("bind flags: %w", err)
}
if err := cfg.Validate(); err != nil {
	return nil, err // Validate's message already says what failed — don't double-wrap
}
```

`%w` keeps the chain inspectable with `errors.Is`/`errors.As`; a `%v` wrap severs it.

## 2. Sentinel errors for conditions callers branch on

Declare package-level sentinels with `errors.New`; expose structured failures as error types.
Callers match with `errors.Is` (sentinels) or `errors.As` (types) — never by comparing message
strings.

```go
var ErrUnknownClient = errors.New("unknown client")
```

## 3. Log with `log/slog`, structured and context-aware

`log/slog` only — no `log.Printf`, no third-party loggers. Pass the request context so handlers
bridged to tracing can correlate, and attach the error as an attribute:

```go
log.LogAttrs(r.Context(), slog.LevelError, "client map load error", slog.Any("error", err))
```

`main` builds one JSON-handler logger writing to stdout; everything else receives a
`*slog.Logger` — never a package-level global.

## 4. Thread `context.Context`; never store it

`ctx context.Context` is the first parameter of any function that does I/O, blocks, or logs.
Derive the root context from process signals in `main` and hand it down:

```go
ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
defer stop()
```

Never keep a context in a struct field — storing it freezes cancellation at construction time.

## 5. Define interfaces at the consumer, and keep them small

The package that calls a dependency declares the interface it needs — one or two methods — and
producers return concrete types. Tests then substitute a hand-written fake (see the `go-testing`
skill):

```go
// Minter turns a (service account, scopes) request into an access token.
type Minter interface {
	Mint(ctx context.Context, saEmail string, scopes []string) (token string, expiresIn int64, err error)
}
```

## 6. Constructors tolerate nil dependencies

`NewX(...)` constructors substitute no-ops for optional dependencies so call sites and tests stay
terse:

```go
func NewBroker(loader *clientmap.Loader, minter token.Minter, log *slog.Logger) *Broker {
	if log == nil {
		log = slog.New(slog.DiscardHandler)
	}
	return &Broker{loader: loader, minter: minter, log: log}
}
```

## 7. Serve HTTP with the stdlib

`net/http` and `http.NewServeMux` with method patterns (Go 1.22+) — no router frameworks.
Middleware is `func(http.Handler) http.Handler`; wrap the response writer to record status, and
keep health probes out of request logs:

```go
mux := http.NewServeMux()
mux.HandleFunc("POST /token", b.handleToken)
mux.HandleFunc("GET /healthz", health)
```

## 8. Configuration: flag > env > default

Every flag has a matching environment variable — the flag name upper-cased, dashes as underscores
(`--client-map-uri` ↔ `CLIENT_MAP_URI`). Parse into one `Config` struct, validate it once at
startup, and fail fast with a wrapped error. For a service or single-purpose binary the stdlib
`flag` package with `os.LookupEnv` fallbacks is enough.

## 9. CLI tools: cobra commands, viper configuration

A program that exposes subcommands is a CLI tool — build its command tree with
`github.com/spf13/cobra` and bind configuration with `github.com/spf13/viper`, keeping the
flag > env > default precedence from rule 8 (viper adds config files between env and default).
Commands use `RunE` and return errors — `main` stays the only place that exits — and silence
cobra's noise on real failures:

```go
root := &cobra.Command{
	Use:           "myapp",
	Short:         "One line on what the tool does.",
	SilenceUsage:  true, // errors are failures, not usage mistakes
	SilenceErrors: true, // main logs the error once
}
v.SetEnvPrefix("MYAPP")
v.SetEnvKeyReplacer(strings.NewReplacer("-", "_"))
v.AutomaticEnv()
if err := v.BindPFlags(cmd.Flags()); err != nil {
	return fmt.Errorf("bind flags: %w", err)
}
```

Give every command a `Short`, a `Long`, and a runnable `Example`, and expose the root command via
a `Root()` accessor — the `go-docs` skill generates the CLI reference from it. Keep business
logic out of `cmd` packages: commands parse and validate input, then call `internal/` packages.

## 10. Keep `go fmt` and `go vet` clean

Code is always `gofmt`-formatted (`go fmt ./...`) and passes `go vet ./...`. Comments state
constraints and invariants the code cannot express — never what the next line does.

For tests and fuzzing see the `go-testing` skill; for project layout and Makefiles see the
`go-project` skill; for releases and CI see the `go-release` skill; for doc comments and CLI
reference generation see the `go-docs` skill.
