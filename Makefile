# Developer tasks. `make help` lists targets.
#
# Node CLIs run straight from node_modules so package-lock.json is the source
# of truth (no npx, no globals). Go developer CLIs are pinned in tools/go.mod
# and run via `go tool` (see tools/README.md).
#
# Tier 1-2 pass-throughs:
#   SKILL=name   restrict to one skill (make eval-trigger SKILL=terraform-style)
#   MODELS=spec  provider names / model ids / "all" (default: anthropic)
#   RUNS=n       Tier-1 runs per query

NPMBIN := ./node_modules/.bin

MODELS ?= anthropic
SKILL_FLAG = $(if $(SKILL),--skill $(SKILL))
RUNS_FLAG  = $(if $(RUNS),--runs $(RUNS))

# plugins/ ships to end users, so scaffolding templates and bundled configs
# stay header-free.
LICENSE_HOLDER := 'Bitwise Media Group'
LICENSE_IGNORE := -ignore '.git/**' \
	-ignore 'node_modules/**' \
	-ignore 'evals-results/**' \
	-ignore '.claude/**' \
	-ignore 'plugins/**' \
	-ignore 'commit.sh'

.PHONY: help lint fmt license eval-static eval-trigger eval-behavior eval report

help: ## list targets
	@awk -F": .*## " "/^[a-z-]+:.*## /{printf \"  %-14s %s\\n\", \$$1, \$$2}" $(MAKEFILE_LIST)

fmt: node_modules ## auto-format the repo with prettier (pinned in package.json)
	@ $(NPMBIN)/prettier --write .

lint: node_modules ## markdownlint all markdown (config: .markdownlint-cli2.yaml)
	@ $(NPMBIN)/markdownlint-cli2 "**/*.md"

license: ## inject SPDX license headers (addlicense, pinned in tools/go.mod)
	@ go tool addlicense -l mit -c $(LICENSE_HOLDER) -s=only $(LICENSE_IGNORE) .

eval-static: ## Tier 0 - frontmatter, manifests, version sync
	./scripts/check-skills.sh

eval-trigger: ## Tier 1 - trigger accuracy + token usage
	python3 tools/eval/run_triggers.py --models "$(MODELS)" $(SKILL_FLAG) $(RUNS_FLAG)

eval-behavior: ## Tier 2 - behavioral cases + token usage
	python3 tools/eval/run_cases.py --models "$(MODELS)" $(SKILL_FLAG)

eval: eval-static eval-trigger eval-behavior ## all three tiers

report: ## regenerate EVALUATION.md files from evals-results/
	python3 tools/eval/report.py

# Install the pinned npm dev tools (prettier, markdownlint) exactly as locked
# in package-lock.json. Re-runs only when package.json / package-lock.json change.
node_modules: package.json package-lock.json
	npm ci
	@touch node_modules
