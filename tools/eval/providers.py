#!/usr/bin/env python3
# Copyright 2026 Bitwise Media Group
# SPDX-License-Identifier: MIT

"""Provider/model matrix and token-counting clients shared by the eval harness.

Token counts come from each provider's official counting API — never a local
tokenizer (tiktoken et al. miscount non-OpenAI models by 15-20%+):

- Anthropic: POST /v1/messages/count_tokens
  https://platform.claude.com/docs/en/build-with-claude/token-counting
- OpenAI:    POST /v1/responses/input_tokens
  https://developers.openai.com/api/docs/guides/token-counting
- Google:    POST /v1beta/models/{model}:countTokens
  https://ai.google.dev/gemini-api/docs/tokens

Counts are cached in evals-results/.token-count-cache.json keyed by
sha256(model + payload), so re-runs and report regeneration cost nothing.
"""

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO / "evals-results"
CACHE_PATH = RESULTS_DIR / ".token-count-cache.json"

# Pricing is USD per 1M tokens (standard tier, cache-miss rates), cached from the
# provider pricing pages. None = provider has not published pricing (preview).
PROVIDERS = {
    "anthropic": {
        "display": "Anthropic",
        # API key preferred; OAuth tokens (claude setup-token / ant auth login)
        # work as a fallback via bearer auth — see auth_headers().
        "env_keys": ["ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN"],
        "runner": "claude",
        "models": [
            {"id": "claude-haiku-4-5", "display": "Claude Haiku 4.5", "input": 1.00, "output": 5.00},
            {"id": "claude-sonnet-4-6", "display": "Claude Sonnet 4.6", "input": 3.00, "output": 15.00},
            {"id": "claude-opus-4-8", "display": "Claude Opus 4.8", "input": 5.00, "output": 25.00},
            {"id": "claude-fable-5", "display": "Claude Fable 5", "input": 10.00, "output": 50.00},
        ],
    },
    "openai": {
        "display": "OpenAI",
        "env_keys": ["OPENAI_API_KEY"],
        "runner": "codex",
        "models": [
            # Spark is a research-preview Codex model; OpenAI has not published API pricing.
            {"id": "gpt-5.3-codex-spark", "display": "GPT-5.3 Codex Spark", "input": None, "output": None},
            {"id": "gpt-5.4-mini", "display": "GPT-5.4 Mini", "input": 0.75, "output": 4.50},
            {"id": "gpt-5.4", "display": "GPT-5.4", "input": 2.50, "output": 15.00},
            {"id": "gpt-5.5", "display": "GPT-5.5", "input": 5.00, "output": 30.00},
        ],
    },
    "google": {
        "display": "Google",
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "runner": "gemini",
        "models": [
            {"id": "gemini-3.1-flash-lite", "display": "Gemini 3.1 Flash-Lite", "input": 0.25, "output": 1.50},
            {"id": "gemini-3-flash-preview", "display": "Gemini 3 Flash (preview)", "input": 0.50, "output": 3.00},
            {"id": "gemini-3.5-flash", "display": "Gemini 3.5 Flash", "input": 1.50, "output": 9.00},
            # <=200K-token tier; long-context requests price higher.
            {"id": "gemini-3.1-pro-preview", "display": "Gemini 3.1 Pro (preview)", "input": 2.00, "output": 12.00},
        ],
    },
}


def select_models(spec):
    """Resolve a --models spec ("anthropic", "all", or comma-separated provider
    names / model ids) to an ordered [(provider_key, model_dict), ...]."""
    tokens = [t.strip() for t in (spec or "anthropic").split(",") if t.strip()]
    if "all" in tokens:
        tokens = list(PROVIDERS)
    selected, seen = [], set()
    for token in tokens:
        if token in PROVIDERS:
            matches = [(token, m) for m in PROVIDERS[token]["models"]]
        else:
            matches = [
                (pk, m) for pk, p in PROVIDERS.items() for m in p["models"] if m["id"] == token
            ]
            if not matches:
                sys.exit(f"error: unknown provider or model in --models: {token!r}")
        for pk, m in matches:
            if m["id"] not in seen:
                seen.add(m["id"])
                selected.append((pk, m))
    return selected


def auth_headers(provider_key):
    """Auth header dict for the provider's counting API, or None when no
    credential is set. Anthropic accepts an API key (x-api-key) or an OAuth
    token (Authorization: Bearer + the oauth beta header)."""
    for env in PROVIDERS[provider_key]["env_keys"]:
        value = os.environ.get(env)
        if not value:
            continue
        if provider_key == "anthropic":
            if env == "ANTHROPIC_API_KEY":
                return {"x-api-key": value, "anthropic-version": "2023-06-01"}
            return {
                "authorization": f"Bearer {value}",
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "oauth-2025-04-20",
            }
        if provider_key == "openai":
            return {"authorization": f"Bearer {value}"}
        if provider_key == "google":
            return {"x-goog-api-key": value}
    return None


def _post_json(url, headers, body, timeout=60):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _count_uncached(provider_key, model_id, text, headers):
    if provider_key == "anthropic":
        resp = _post_json(
            "https://api.anthropic.com/v1/messages/count_tokens",
            headers,
            {"model": model_id, "messages": [{"role": "user", "content": text}]},
        )
        return resp["input_tokens"]
    if provider_key == "openai":
        resp = _post_json(
            "https://api.openai.com/v1/responses/input_tokens",
            headers,
            {"model": model_id, "input": text},
        )
        return resp["input_tokens"]
    if provider_key == "google":
        resp = _post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:countTokens",
            headers,
            {"contents": [{"parts": [{"text": text}]}]},
        )
        return resp["totalTokens"]
    raise ValueError(f"unknown provider: {provider_key}")


class TokenCounter:
    """count() returns the provider-reported input-token count for a payload,
    or None when the provider key is missing or the API call fails."""

    def __init__(self):
        self._cache = {}
        self._warned = set()
        if CACHE_PATH.is_file():
            try:
                self._cache = json.loads(CACHE_PATH.read_text())
            except json.JSONDecodeError:
                self._cache = {}

    def count(self, provider_key, model_id, text):
        digest = hashlib.sha256(f"{model_id}\0{text}".encode()).hexdigest()
        if digest in self._cache:
            return self._cache[digest]
        headers = auth_headers(provider_key)
        if not headers:
            self._warn(provider_key, "no API key or OAuth token set; token counts omitted")
            return None
        try:
            tokens = _count_uncached(provider_key, model_id, text, headers)
        except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
            self._warn(f"{provider_key}/{model_id}", f"count_tokens failed: {exc}")
            return None
        self._cache[digest] = tokens
        return tokens

    def _warn(self, scope, message):
        if scope not in self._warned:
            self._warned.add(scope)
            print(f"  warn: [{scope}] {message}", file=sys.stderr)

    def save(self):
        RESULTS_DIR.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(self._cache, indent=2, sort_keys=True) + "\n")


def input_cost_usd(model, input_tokens):
    """Estimated input cost in USD, or None when pricing/count is unavailable."""
    if input_tokens is None or model["input"] is None:
        return None
    return round(input_tokens / 1_000_000 * model["input"], 6)


def usage_cost_usd(model, usage):
    """Cost of a measured {input_tokens, output_tokens} usage dict, or None."""
    if not usage or model["input"] is None or model["output"] is None:
        return None
    cost = (usage.get("input_tokens") or 0) / 1_000_000 * model["input"]
    cost += (usage.get("output_tokens") or 0) / 1_000_000 * model["output"]
    return round(cost, 6)


def load_results(path, plugin, skill):
    """Load a schema-2 results file, or initialise one (legacy list files from
    the pre-token-tracking harness are replaced)."""
    if path.is_file():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict) and data.get("schema") == 2:
                return data
        except json.JSONDecodeError:
            pass
    return {"schema": 2, "plugin": plugin, "skill": skill, "models": {}}
