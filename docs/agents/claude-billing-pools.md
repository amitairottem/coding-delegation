# Claude billing pools

The router treats Claude subscription usage and Anthropic API-key usage as two separate pools.

## Tool IDs

- `claude` — Claude Code authenticated with the Claude subscription (`claude auth login --claudeai`). This is the existing tool ID and remains backwards-compatible.
- `claude_api` — Claude Code launched with `ANTHROPIC_API_KEY` present. This is a separate, opt-in pool.
- `claude_subscription` is accepted as a preference alias for `claude`.

## Billing safety

Subscription launches return launch metadata with:

```yaml
auth: claude_subscription
unset_env:
  - ANTHROPIC_API_KEY
```

A runner must actually remove `ANTHROPIC_API_KEY` from the child process environment. Anthropic documents that an API key can take precedence over subscription authentication, so leaving it inherited could silently move a job onto API billing.

API launches return:

```yaml
auth: anthropic_api_key
require_env:
  - ANTHROPIC_API_KEY
```

The key itself is never copied into routing output or logs. A runner must fail closed if a required variable is absent.

## Default policy

`claude_api` is disabled by default and its default plan is `extra`. That means simply having an API key in the environment cannot make the router spend against the API pool. A user must explicitly enable the tool and also allow extra spend according to the existing routing policy.

If an organization has a separately enforced hard billing cap and intentionally wants to treat API credits as included capacity, the user may set the pool's plan to `included`. The router cannot independently verify the remaining Anthropic API-credit balance, so that choice should only be made when external billing controls make overage impossible or acceptable.

Example:

```yaml
preferences:
  order:
    - claude_subscription
    - claude_api
    - codex
routing:
  extra_spend: per_job
  tools:
    claude:
      enabled: true
      plan: included
    claude_api:
      enabled: true
      plan: extra
```

This expresses the intended order: subscription capacity first, then the separately authorized API pool, then other tools.

## Logs

Routing logs include `billing_pool` (`claude_subscription` or `claude_api`) so a later audit can distinguish which Claude capacity was selected without storing credentials.
