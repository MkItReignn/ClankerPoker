# LLM Prompt Token Analysis

This document provides a comprehensive analysis of token usage in the poker LLM prompt system, explains how LLM APIs actually work, and outlines real optimization strategies based on our architecture.

## Table of Contents

1. [Critical Understanding: LLM Statelessness](#critical-understanding-llm-statelessness)
2. [Token Counting Methodology](#token-counting-methodology)
3. [Current Implementation: Fresh Calls](#current-implementation-fresh-calls)
4. [Alternative Approach: Persistent Conversations](#alternative-approach-persistent-conversations)
5. [Token Cost Comparison](#token-cost-comparison)
6. [Why Fresh Calls Are Optimal for Poker](#why-fresh-calls-are-optimal-for-poker)
7. [Real Optimization Opportunities](#real-optimization-opportunities)
8. [Recommendations](#recommendations)

---

## Critical Understanding: LLM Statelessness

### LLMs Are Stateless

**LLMs don't "remember" anything between API calls.** The entire conversation history is re-sent with each request.

Even in a "persistent conversation" pattern, the client code must resend all previous messages:

```
Call 1: [system, user₁]
Call 2: [system, user₁, assistant₁, user₂]
Call 3: [system, user₁, assistant₁, user₂, assistant₂, user₃]
```

**Each API call includes:**
- The full system prompt (every time)
- All previous user messages (every time)
- All previous assistant responses (every time)
- The new user message

### What This Means for Token Costs

There are two architectural approaches:

1. **Fresh Calls** (Current): Each decision is an independent API call
   - No conversation history maintained
   - Each call sends: system prompt + current game state
   - Simple, stateless architecture

2. **Persistent Conversations** (Not used): Maintain conversation history across decisions
   - Each call sends: system prompt + all previous messages + current game state
   - Requires state management in client code
   - Context window grows with each decision

**The key question:** Which approach uses fewer tokens for poker?

---

## Token Counting Methodology

### How Tokens Were Calculated

LLMs use **tokenization** to convert text into numerical representations. Different models use different tokenizers, but they share similar characteristics for English text.

**Approximation Method Used:**
```
tokens ≈ character_count ÷ 4
```

This approximation is standard for English text and provides estimates within ±10% of actual values.

### Why This Approximation Works

- Claude uses byte-pair encoding (BPE) similar to GPT's tokenizer
- Common English words typically tokenize to 1-2 tokens
- Punctuation and special characters may be 1 token each
- The 4 chars/token ratio is a well-established heuristic

### Measurement Code

```python
from src.config.poker.prompt import PokerPromptConfigLoader

def approx_tokens(text: str) -> int:
    return len(text) // 4

loader = PokerPromptConfigLoader()
config = loader.load()

# Measure system prompt components
sys = config.system_prompt
print(f"identity: ~{approx_tokens(sys.identity)} tokens ({len(sys.identity)} chars)")
print(f"context_format_guide: ~{approx_tokens(sys.context_format_guide)} tokens")
# ... etc
```

---

## Current Implementation: Fresh Calls

Our implementation uses **independent API calls for each decision**, with no conversation history maintained between calls.

### Token Breakdown

**System Prompt Components (Sent Every Decision):**

| Component | Characters | ~Tokens | Purpose |
|-----------|------------|---------|---------|
| `identity` | 775 | ~193 | Establishes elite poker player persona |
| `context_format_guide` | 2,286 | ~571 | Teaches how to read game context |
| `history_notation` | 1,741 | ~435 | Explains action shorthand (F, X, C, B, R, AI) |
| `decision_framework` | 2,363 | ~590 | 9-category systematic thinking process |
| `personality_section` | 233 | ~58 | Optional personality injection |
| **TOTAL** | **7,398** | **~1,791** | |

**User Prompt Components (Sent Every Decision):**

| Component | Characters | ~Tokens | Purpose |
|-----------|------------|---------|---------|
| `response_format` | 540 | ~135 | Instructions for ACTION + REASONING format |
| `complete_example` | 1,260 | ~315 | Full example showing correct response |
| `game_state` | ~300 | ~76 | Current hand info, board, pot, opponents |
| `current_hand_actions` | ~104 | ~26 | Actions so far in this hand |
| `history (1 prev hand)` | ~196 | ~49 | Minimal opponent pattern data |
| `history (5 prev hands)` | ~916 | ~229 | Full opponent pattern data |

**Total Per Decision:**

| Scenario | System | User | Total |
|----------|--------|------|-------|
| Minimal (no history) | 1,791 | 526 | 2,317 |
| With 1 previous hand | 1,791 | 602 | 2,393 |
| With 5 previous hands | 1,791 | 781 | 2,572 |

### Architecture

```
Decision 1:
┌─────────────────────────────────────────┐
│ API Call 1                              │
│ system: [full system prompt] = 1,791    │
│ user: [game state + templates] = 526    │
│ TOTAL: 2,317 tokens                     │
└─────────────────────────────────────────┘

Decision 2:
┌─────────────────────────────────────────┐
│ API Call 2 (independent)                │
│ system: [full system prompt] = 1,791    │
│ user: [game state + templates] = 526    │
│ TOTAL: 2,317 tokens                     │
└─────────────────────────────────────────┘

Decision n:
┌─────────────────────────────────────────┐
│ API Call n (independent)                │
│ system: [full system prompt] = 1,791    │
│ user: [game state + templates] = 526    │
│ TOTAL: 2,317 tokens                     │
└─────────────────────────────────────────┘
```

**Total for n decisions: n × 2,317**

---

## Alternative Approach: Persistent Conversations

What if we maintained conversation history between decisions?

### With Current Prompts

```
Decision 1:
┌─────────────────────────────────────────┐
│ system: [full system prompt] = 1,791    │
│ user₁: [game state + templates] = 526   │
│ TOTAL: 2,317 tokens                     │
└─────────────────────────────────────────┘

Decision 2:
┌─────────────────────────────────────────┐
│ system: [full system prompt] = 1,791    │
│ user₁: [game + templates] = 526         │
│ assistant₁: [response] = ~100           │
│ user₂: [game + templates] = 526         │
│ TOTAL: 2,943 tokens                     │
└─────────────────────────────────────────┘

Decision 3:
┌─────────────────────────────────────────┐
│ system: [full system prompt] = 1,791    │
│ user₁: [game + templates] = 526         │
│ assistant₁: [response] = ~100           │
│ user₂: [game + templates] = 526         │
│ assistant₂: [response] = ~100           │
│ user₃: [game + templates] = 526         │
│ TOTAL: 3,569 tokens                     │
└─────────────────────────────────────────┘
```

**Pattern:** Each decision adds 626 tokens (user 526 + assistant 100)

**Total for n decisions:**
```
Decision n tokens = 2,317 + (n-1) × 626

Sum for all n decisions = Σ [2,317 + (i-1)×626] for i=1 to n
                        = n × 2,317 + 626 × n(n-1)/2
                        = n × 2,317 + 313n(n-1)
```

### With Optimized Prompts (Templates in System)

What if we moved `response_format` and `complete_example` to the system prompt?

```
Decision 1:
┌─────────────────────────────────────────┐
│ system: [system + templates] = 2,241    │
│ user₁: [game state only] = 76           │
│ TOTAL: 2,317 tokens                     │
└─────────────────────────────────────────┘

Decision 2:
┌─────────────────────────────────────────┐
│ system: [system + templates] = 2,241    │
│ user₁: [game only] = 76                 │
│ assistant₁: [response] = ~100           │
│ user₂: [game only] = 76                 │
│ TOTAL: 2,493 tokens                     │
└─────────────────────────────────────────┘

Decision 3:
┌─────────────────────────────────────────┐
│ system: [system + templates] = 2,241    │
│ user₁: [game only] = 76                 │
│ assistant₁: [response] = ~100           │
│ user₂: [game only] = 76                 │
│ assistant₂: [response] = ~100           │
│ user₃: [game only] = 76                 │
│ TOTAL: 2,669 tokens                     │
└─────────────────────────────────────────┘
```

**Pattern:** Each decision adds 176 tokens (user 76 + assistant 100)

**Total for n decisions:**
```
Decision n tokens = 2,317 + (n-1) × 176

Sum for all n decisions = n × 2,317 + 176 × n(n-1)/2
                        = n × 2,317 + 88n(n-1)
```

---

## Token Cost Comparison

### For 100 Decisions

| Approach | Calculation | Total Tokens |
|----------|-------------|--------------|
| **Fresh Calls (Current)** | 100 × 2,317 | **231,700** |
| Persistent (Current Prompts) | 100×2,317 + 313×100×99 | **3,336,400** |
| Persistent (Optimized) | 100×2,317 + 88×100×99 | **1,102,900** |

**Results:**
- Persistent with current prompts: **14.4x MORE expensive** than fresh calls
- Persistent optimized: **4.8x MORE expensive** than fresh calls
- Fresh calls are the clear winner

### Break-Even Analysis

When does persistent optimized become cheaper than fresh?

```
Fresh total: n × 2,317
Persistent optimized: n × 2,317 + 88n(n-1)

Break-even when history overhead is negligible:
88n(n-1) ≈ 0 compared to 2,317n

This happens when:
88(n-1) << 2,317
n << 27.3
```

**Break-even: ~27 decisions**

- **Fewer than 27 decisions:** Fresh calls are cheaper
- **More than 27 decisions:** Persistent optimized is cheaper
- **BUT:** Typical poker tournaments have 50-200+ decisions

### Visualization

```
Token Cost by Number of Decisions

Tokens
(thousands)
    │
3500│                                          Persistent (current)
    │                                        ╱
3000│                                      ╱
    │                                    ╱
2500│                                  ╱
    │                                ╱
2000│                              ╱
    │                            ╱
1500│                          ╱
    │                        ╱        Persistent (optimized)
1000│                      ╱          ╱
    │                    ╱          ╱
 500│                  ╱          ╱
    │        Fresh calls (linear)
   0├─────────────────────────────────────────────> Decisions
    0    25    50    75    100   125   150
         ↑
    Break-even point (~27)
```

---

## Why Fresh Calls Are Optimal for Poker

### 1. Decisions Are Independent

Each poker decision is self-contained:
- New hand = new situation
- Game state includes recent history already
- No benefit to LLM "remembering" its previous responses

**Example:** Knowing that the LLM folded hand #47 doesn't help it decide hand #48. The game state already includes relevant opponent patterns.

### 2. No Context Window Issues

With fresh calls:
- Context window never grows
- No need to truncate history
- No risk of hitting token limits
- Predictable token costs

### 3. Simpler Architecture

Fresh calls require:
- No conversation state management
- No message history tracking
- No context window monitoring
- Easier debugging (each call is isolated)

### 4. Cost Efficiency

For 100 decisions:
- Fresh: 231,700 tokens
- Persistent optimized: 1,102,900 tokens
- **Fresh is 4.8x cheaper**

### 5. Parallelization Potential

With independent calls, we could theoretically:
- Process multiple decisions concurrently (in parallel games)
- Cache and reuse system prompts (depending on API provider)
- Scale horizontally without state synchronization

---

## Real Optimization Opportunities

Since we're using fresh calls, the optimization strategy is different from what was previously documented. We can't benefit from "moving templates to system prompt" because the system prompt is resent every time anyway.

### Tier 1: Compress Notation Guide

**What:** Replace verbose notation explanations with compact table format

**Current format (~435 tokens):**
```
=== ACTION NOTATION ===

SHORTHAND CODES:
  F          = Fold (surrender hand)
  X          = Check (pass, no bet)
  C          = Call (match current bet)
  B<amount>  = Bet (e.g., B100 = bet 100 chips)
  R<amount>  = Raise TO amount (e.g., R300 = raise to 300 total)
  AI<amount> = All-in for amount (e.g., AI500 = all-in for 500)

POSITION ABBREVIATIONS:
  BTN = Button (dealer, acts last post-flop - best position)
  SB  = Small Blind (forced half-bet, first post-flop - worst position)
  ... (continues with examples and explanations)
```

**Compressed format (~200 tokens):**
```
NOTATION: F=fold X=check C=call B<n>=bet R<n>=raise AI<n>=allin
POSITIONS: BTN=Button SB=SmallBlind BB=BigBlind UTG=UnderTheGun CO=Cutoff
HISTORY: <PHASE>: <player>(<pos>):<action>, ... | "?" = your turn
```

**Token impact:** ~235 tokens saved per decision (10% reduction)

**Quality risk:** Low. LLMs handle compressed notation well, especially with examples.

**Implementation:** Medium. Requires rewriting YAML content.

---

### Tier 2: Adaptive History Depth

**What:** Dynamically adjust how much hand history to include based on game state

**Current behavior:** Always includes up to 5 previous hands (~229 tokens max)

**Optimized behavior:**
- **Early tournament (hands 1-5):** No history needed (no patterns established yet)
- **Heads-up:** Only include hands with the remaining opponent
- **Showdown hands only:** Prioritize hands where cards were revealed (more informative)

**Token impact:** 50-150 tokens saved per decision (2-6% reduction)

**Quality risk:** Low-Medium. Less history = less opponent modeling data, but irrelevant history adds noise.

**Implementation:** Medium. Requires filtering logic in history formatter.

---

### Tier 3: Reduce Decision Framework

**What:** Shorten or simplify the 9-category decision framework

**Current framework (~590 tokens):**
- 9 numbered categories
- 4 bullet points per category
- Detailed guidance on each thinking step

**Options:**

| Option | Description | Tokens | Quality Impact |
|--------|-------------|--------|----------------|
| A (Current) | Full 9-category framework | 590 | Baseline |
| B (Minimal) | Just category names, no bullets | ~150 | Low risk |
| C (Example-driven) | Remove framework, rely on example | 0 | Medium risk |

**Token impact:** Up to 590 tokens saved per decision (25% reduction)

**Quality risk:** Medium-High. The framework guides structured reasoning. Removing it may result in:
- Skipped analysis categories
- Less consistent output format
- Reduced reasoning quality

**When to consider:** Only if Tiers 1-2 don't provide sufficient savings AND you're willing to A/B test quality impact.

---

### Tier 4: Compress Context Format Guide

**What:** Reduce verbosity in the guide that teaches the LLM to read game context

**Current:** ~571 tokens of detailed explanation with examples

**Compressed:** ~300 tokens with minimal examples (rely on self-evident structure)

**Token impact:** ~271 tokens saved per decision (12% reduction)

**Quality risk:** Medium. The guide ensures correct parsing of game state. Compression could lead to misinterpretation.

**When to consider:** Only after validating that LLM correctly parses game state with minimal guidance.

---

### Combined Optimization Impact

| Tiers | Per-Decision Savings | % Reduction | 100 Decisions | Risk |
|-------|---------------------|-------------|---------------|------|
| Tier 1 | ~235 | 10% | 23,500 | Low |
| Tiers 1+2 | ~285-385 | 12-17% | 28,500-38,500 | Low |
| Tiers 1+2+3 | ~875-975 | 38-42% | 87,500-97,500 | Medium |
| All Tiers | ~1,146-1,346 | 49-58% | 114,600-134,600 | Medium-High |

---

## Recommendations

### For Immediate Implementation (Low Risk)

**Tier 1: Compress Notation Guide**
- 10% token reduction per decision
- No quality risk (LLMs handle compact notation well)
- Medium implementation effort (YAML rewrite)

**Estimated savings for 100 decisions:** 23,500 tokens (~10% reduction)

### For Moderate Optimization (Low-Medium Risk)

**Tiers 1 + 2: Notation + Adaptive History**
- 12-17% token reduction per decision
- Low quality risk (removes noise, keeps signal)
- Particularly effective for early-game and heads-up situations

**Estimated savings for 100 decisions:** 28,500-38,500 tokens (~12-17% reduction)

### For Aggressive Optimization (Medium-High Risk)

**Tiers 1 + 2 + 3: Add Framework Reduction**
- 38-42% token reduction per decision
- Requires A/B testing to validate quality impact
- May reduce reasoning consistency

**Estimated savings for 100 decisions:** 87,500-97,500 tokens (~38-42% reduction)

**Important:** Only pursue this after testing shows minimal quality degradation.

### NOT Recommended

**Switching to Persistent Conversations**
- Would require significant architectural changes
- 4.8x MORE expensive than current approach (even optimized)
- Adds complexity (state management, context window monitoring)
- Provides zero benefit for poker (decisions are independent)

---

## Summary

### Key Takeaways

1. **LLMs are stateless** - The entire conversation history is resent with each API call

2. **Fresh calls are optimal for poker** - Because decisions are independent and conversation history provides no value

3. **Persistent conversations would be 4.8x more expensive** - Even with prompt optimization

4. **Real optimizations come from compression** - Not architectural changes

5. **Safe optimizations exist** - Tier 1 provides 10% savings with no quality risk

### Comparison Table

| Approach | Tokens per Decision | 100 Decisions | Architecture Complexity |
|----------|---------------------|---------------|-------------------------|
| **Current (Fresh)** | 2,317 | 231,700 | Simple |
| Persistent (Optimized) | Grows: 2,317-4,493 | 1,102,900 | Complex |
| Fresh + Tier 1 | ~2,082 | 208,200 | Simple |
| Fresh + Tiers 1+2 | ~1,932-2,032 | 193,200-203,200 | Simple |
| Fresh + Tiers 1+2+3 | ~1,342-1,442 | 134,200-144,200 | Simple |

**Bottom Line:** Keep the current fresh calls architecture and focus on prompt compression for optimization.
