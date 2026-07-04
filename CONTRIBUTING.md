# Contributing to Kalshi Trading Bot

## Commit Guidelines for AI/Perplexity Pushes

When using Perplexity or other AI systems to push commits to this repository, follow these guidelines to maintain a clear audit trail:

### Commit Message Format

```
[perplexity/MODEL] Subject line under 50 characters

LLM-Model: <gpt-4|claude-3|llama-2|etc>
Perplexity-Session: <session-id or task-id>
Context: <brief description of what the AI was tasked to do>
```

### Examples

**Example 1: GPT-4 via Perplexity**
```
[perplexity/gpt-4] Add trading API integration

LLM-Model: gpt-4
Perplexity-Session: ***
Context: Generated Kalshi API client wrapper
```

**Example 2: Claude via Perplexity**
```
[perplexity/claude-3] Fix market data parsing logic

LLM-Model: claude-3-opus
Perplexity-Session: pplx-xyz789
Context: Debugged JSON parsing in market response handler
```

### Required Information

- **LLM Model**: Always specify which underlying model Perplexity used
  - Ask Perplexity: "What LLM model are you using?" or check the API metadata
  - Common options: `gpt-4`, `claude-3-opus`, `claude-3-sonnet`, `llama-2`, etc.

- **Perplexity Session**: Include the session ID/reference if available
  - Helps trace the original request and context

- **Context**: Briefly explain what task the AI was asked to perform
  - Helps reviewers understand intent behind changes

### Why This Matters

This repo uses AI for code generation and updates. Tracking which LLM was used helps us:
- Understand which models produce better code for this domain
- Identify patterns in errors or issues
- Maintain transparency about AI-assisted development
- Reproduce issues if needed

### Pull Request Expectations

If your Perplexity commit is part of a PR:
1. Include the commit message details in the PR description
2. Flag that it's AI-generated (`[AI-Generated]` in title if applicable)
3. Be prepared to explain what the AI did and verify it's correct

---

**Questions?** Check the `.gitmessage` template or contact maintainers.
