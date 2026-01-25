# Event Schema Reference

Complete reference of all published event types, payloads, and domain models for consumers (TUI, web, replay systems, etc.).

---

## Event Envelope

Every published event follows this structure:

```python
@dataclass(frozen=True, slots=True)
class PublishedEvent:
    event_type: EventType          # Which event occurred
    details: dict[str, Any]        # Event-specific payload (see below)
    game_state: dict[str, Any]     # Full game snapshot (see Game State section)
    metadata: PublishedEventMetadata
```

### Metadata

```python
@dataclass(frozen=True, slots=True)
class PublishedEventMetadata:
    game_id: str
    hand_number: int
    timestamp: datetime       # ISO format string in dict
    sequence: int             # Monotonically increasing
```

---

## Event Types

```python
class EventType(StrEnum):
    GAME_STARTED = "game_started"
    GAME_COMPLETED = "game_completed"
    HAND_STARTED = "hand_started"
    HAND_COMPLETED = "hand_completed"
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"
    BLINDS_POSTED = "blinds_posted"
    ACTION_APPLIED = "action_applied"
    HOLE_CARDS_DEALT = "hole_cards_dealt"
    PLAYER_TO_ACT = "player_to_act"
```

---

## Event Details Payloads

### GAME_STARTED

```python
{
    "player_count": int,
    "starting_chips": int
}
```

### GAME_COMPLETED

```python
{
    "winner_id": str,
    "winner_name": str,
    "total_hands": int,
    "final_standings": [
        {
            "player_id": str,
            "player_name": str,
            "finish_position": int,
            "elimination_hand": int | None
        },
        ...
    ]
}
```

### HAND_STARTED

```python
{
    "hand_number": int,
    "button_seat": int,         # 0-5
    "sb_seat": int,             # 0-5
    "bb_seat": int              # 0-5
}
```

### HOLE_CARDS_DEALT

```python
{
    "<player_id>": {
        "player_id": str,
        "player_name": str,
        "cards": [
            {"suit": str, "rank": str},
            {"suit": str, "rank": str}
        ],
        "deal_order": int
    },
    ...
}
```

### BLINDS_POSTED

```python
{
    "small_blind": {
        "player_id": str,
        "player_name": str,
        "amount": int
    },
    "big_blind": {
        "player_id": str,
        "player_name": str,
        "amount": int
    }
}
```

### ROUND_STARTED

```python
{
    "phase": str,               # "pre_flop" | "flop" | "turn" | "river" | "showdown"
    "new_cards": [
        {"suit": str, "rank": str},
        ...
    ]
}
```

### ROUND_COMPLETED

```python
{}   # Empty payload
```

### PLAYER_TO_ACT

```python
{
    "player_id": str,
    "player_name": str,
    "available_actions": [
        # One or more of:
        {"action_type": "fold"},
        {"action_type": "check"},
        {"action_type": "call", "call_amount": int},
        {"action_type": "bet", "min_bet_amount": int, "max_bet_amount": int},
        {"action_type": "raise", "min_raise_amount": int, "max_raise_amount": int},
        {"action_type": "all_in", "all_in_amount": int}
    ]
}
```

### ACTION_APPLIED

```python
{
    "player_id": str,
    "player_name": str,
    "action_type": str,         # "fold" | "check" | "call" | "bet" | "raise" | "all_in"
    "amount": int | None,
    "narration": {
        "thought_process": str  # LLM's reasoning (200-500 words)
    } | None
}
```

### HAND_COMPLETED

```python
{
    "winners": [
        {
            "player_id": str,
            "player_name": str,
            "amount": int
        },
        ...
    ],
    "eliminated": [
        {
            "player_id": str,
            "player_name": str,
            "finish_position": int
        },
        ...
    ],
    "showdown": [                   # null if no showdown (everyone folded)
        {
            "player_id": str,
            "player_name": str,
            "hole_cards": [
                {"suit": str, "rank": str},
                {"suit": str, "rank": str}
            ],
            "hand_evaluation": {
                "rank": int,        # 1-10 (see HandRank)
                "cards_used": [
                    {"suit": str, "rank": str},
                    ...
                ],
                "kickers": [int, ...]
            }
        },
        ...
    ] | None,
    "pot_amount": int,
    "player_outcomes": [
        {
            "player_id": str,
            "player_name": str,
            "chips_won": int,
            "final_stack": int
        },
        ...
    ]
}
```

---

## Game State Snapshot

Every event includes the full `game_state` dict:

```python
{
    "identity": {
        "id": str,
        "created_at": str,          # ISO datetime
        "updated_at": str,
        "started_at": str | None,
        "completed_at": str | None,
        "status": str,              # "in_progress" | "completed" | "cancelled"
        "seed": int
    },
    "hand_state": {
        "hand_number": int,
        "current_phase": str,       # "pre_flop" | "flop" | "turn" | "river" | "showdown"
        "community_cards": [
            {"suit": str, "rank": str},
            ...
        ]
    },
    "pot_state": {
        "main_pot": {
            "amount": int,
            "eligible_player_ids": [str, ...]
        },
        "side_pots": [
            {
                "amount": int,
                "eligible_player_ids": [str, ...]
            },
            ...
        ],
        "total": int
    },
    "betting_state": {
        "last_raise_increment": int,
        "position_to_act": int      # -1 if no one to act
    },
    "button_seat": int,             # 0-5
    "blind_level": {
        "small_blind": int,
        "big_blind": int,
        "level": int
    },
    "players": [
        {
            "id": str,
            "name": str,
            "bot_id": str,
            "seat": int,            # 0-5
            "remaining_chips": int,
            "hole_cards": [
                {"suit": str, "rank": str},
                {"suit": str, "rank": str}
            ] | None,
            "betting_status": str,  # "needs_action" | "acted"
            "participation_status": str,  # "in_hand" | "folded" | "eliminated"
            "total_invested_this_hand": int,
            "is_all_in": bool,
            "hands_played": int,
            "elimination_hand_number": int | None,
            "table_finish_position": int | None
        },
        ...
    ],
    "player_to_act_id": str | None
}
```

---

## Domain Value Types

### Card

```python
{
    "suit": str,    # "hearts" | "diamonds" | "clubs" | "spades"
    "rank": str     # "2"-"10" | "J" | "Q" | "K" | "A"
}
```

### Suit Display

| Suit | Value | Symbol | Color |
|------|-------|--------|-------|
| Spades | `"spades"` | ♠ | White |
| Hearts | `"hearts"` | ♥ | Red |
| Diamonds | `"diamonds"` | ♦ | Red |
| Clubs | `"clubs"` | ♣ | White |

### GamePhase

| Phase | Value | Community Cards |
|-------|-------|-----------------|
| Pre-flop | `"pre_flop"` | 0 |
| Flop | `"flop"` | 3 |
| Turn | `"turn"` | 4 |
| River | `"river"` | 5 |
| Showdown | `"showdown"` | 5 |

### ActionType

| Action | Value | Has Amount |
|--------|-------|------------|
| Fold | `"fold"` | No |
| Check | `"check"` | No |
| Call | `"call"` | No (implicit) |
| Bet | `"bet"` | Yes |
| Raise | `"raise"` | Yes |
| All-in | `"all_in"` | Yes |
| Post SB | `"post_small_blind"` | Yes |
| Post BB | `"post_big_blind"` | Yes |

### HandRank

| Rank | Value | Name |
|------|-------|------|
| 1 | `HIGH_CARD` | High Card |
| 2 | `PAIR` | Pair |
| 3 | `TWO_PAIR` | Two Pair |
| 4 | `THREE_OF_A_KIND` | Three of a Kind |
| 5 | `STRAIGHT` | Straight |
| 6 | `FLUSH` | Flush |
| 7 | `FULL_HOUSE` | Full House |
| 8 | `FOUR_OF_A_KIND` | Four of a Kind |
| 9 | `STRAIGHT_FLUSH` | Straight Flush |
| 10 | `ROYAL_FLUSH` | Royal Flush |

### Player Status

**BettingRoundActionStatus:**
- `"needs_action"` - Player must act this round
- `"acted"` - Player has acted this round

**HandParticipationStatus:**
- `"in_hand"` - Active in current hand
- `"folded"` - Folded this hand
- `"eliminated"` - Out of tournament (0 chips)

### Seat

Integer 0-5. Up to 6 players supported.

---

## Event Flow Example

Typical event sequence for a hand:

```
1. HAND_STARTED        → New hand, button position set
2. HOLE_CARDS_DEALT    → Each player receives 2 cards
3. BLINDS_POSTED       → SB and BB posted
4. PLAYER_TO_ACT       → First player to act (UTG or SB in heads-up)
5. ACTION_APPLIED      → Player takes action
6. PLAYER_TO_ACT       → Next player...
   ... (repeat 5-6 until betting complete)
7. ROUND_COMPLETED     → Pre-flop betting done
8. ROUND_STARTED       → Flop dealt (3 cards)
9. PLAYER_TO_ACT       → First to act post-flop
   ... (repeat action/player_to_act)
10. ROUND_COMPLETED    → Flop betting done
11. ROUND_STARTED      → Turn dealt (1 card)
    ... (repeat)
12. ROUND_COMPLETED    → Turn betting done
13. ROUND_STARTED      → River dealt (1 card)
    ... (repeat)
14. ROUND_COMPLETED    → River betting done
15. HAND_COMPLETED     → Winners, showdown results, eliminations
```

If everyone folds before showdown, skip to HAND_COMPLETED with no showdown data.

---

## Consumer Display Mapping

| Event | UI Updates |
|-------|------------|
| `GAME_STARTED` | Initialize all player panels |
| `HAND_STARTED` | Reset bets, update hand #, move dealer button |
| `HOLE_CARDS_DEALT` | Show face-down cards on panels |
| `BLINDS_POSTED` | Update bets, log blind posts |
| `ROUND_STARTED` | Update phase, show community cards |
| `PLAYER_TO_ACT` | Highlight active player |
| `ACTION_APPLIED` | Update chips/bets, log action + narration |
| `ROUND_COMPLETED` | Clear active indicator |
| `HAND_COMPLETED` | Show winners, reveal cards, update stacks |
| `GAME_COMPLETED` | Show tournament winner |

---

## Sentinel Value

`None` pushed to queue signals end of event stream (game complete or error).

```python
async def consume_events(self) -> None:
    while True:
        event = await self._queue.get()
        if event is None:
            break
        await self._handle_event(event)
```
