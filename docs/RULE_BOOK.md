# Texas Hold'em No-Limit Tournament Rules

> **Purpose:** Complete rulebook for LLM-powered poker bots in ClankerPoker
> **Format:** Tournament-style only (no cash games)
> **Players:** 4-6 per table

---

## Table of Contents

1. [Game Overview](#1-game-overview)
2. [Card and Deck Mechanics](#2-card-and-deck-mechanics)
3. [Table Positions](#3-table-positions)
4. [Blinds](#4-blinds)
5. [Dealing Procedure](#5-dealing-procedure)
6. [Betting Rounds](#6-betting-rounds)
7. [Player Actions](#7-player-actions)
   - 7.9 [Action Availability Conditions](#79-action-availability-conditions)
8. [Betting Rules and Constraints](#8-betting-rules-and-constraints)
9. [All-In Situations and Side Pots](#9-all-in-situations-and-side-pots)
10. [Showdown](#10-showdown)
11. [Hand Rankings](#11-hand-rankings)
12. [Pot Award and Split Pots](#12-pot-award-and-split-pots)
13. [Player Elimination](#13-player-elimination)
14. [Button and Blind Movement](#14-button-and-blind-movement)
15. [Tournament Progression](#15-tournament-progression)
16. [End Conditions](#16-end-conditions)
17. [Complete Hand Example](#17-complete-hand-example)
18. [Edge Cases Reference](#18-edge-cases-reference)
19. [Glossary](#19-glossary)

---

## 1. Game Overview

### 1.1 What is Texas Hold'em No-Limit?

Texas Hold'em is a community card poker game where each player receives two private cards ("hole cards") and shares five community cards with all other players. The objective is to make the best five-card poker hand using any combination of the seven available cards (2 hole cards + 5 community cards).

### 1.2 No-Limit Betting

"No-Limit" means there is no maximum bet. A player may bet any amount up to and including all of their chips at any time when it is their turn to act.

### 1.3 Tournament Format

In tournament format:
- All players start with an equal number of chips
- Chips have no cash value during play
- Blinds increase on a fixed schedule
- Players are eliminated when they lose all chips
- The tournament ends when one player has all chips
- Prizes are awarded based on finish position, not chip count

### 1.4 Key Terminology

| Term | Definition |
|------|------------|
| **Hole Cards** | The two private cards dealt to each player |
| **Community Cards** | The five shared cards dealt face-up on the board |
| **The Board** | The community cards (flop + turn + river) |
| **Pot** | The total chips wagered in the current hand |
| **Stack** | A player's total chip count |
| **Action** | A player's turn to act, or the decision they make |

---

## 2. Card and Deck Mechanics

### 2.1 The Deck

- Standard 52-card deck
- Four suits: Spades (♠), Hearts (♥), Diamonds (♦), Clubs (♣)
- Suits have NO ranking - they are completely equal
- 13 ranks per suit: 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A

### 2.2 Card Rankings (Low to High)

```
2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A
```

**Special Case - The Ace:**
- Ace is the highest card (above King)
- Ace can also be used as low card (value 1) ONLY in the straight A-2-3-4-5 (called "the wheel")
- Ace is NOT low in any other context

### 2.3 Shuffle and Cut

- Deck is shuffled before each hand
- In digital implementation, use cryptographically secure randomization
- Each hand uses a fresh, fully shuffled deck

---

## 3. Table Positions

### 3.1 The Dealer Button

- A marker ("button") indicates the nominal dealer position
- The button rotates clockwise after each hand
- The button determines all other positions and betting order

### 3.2 Position Names (Relative to Button)

For a 6-player table, positions are:

| Position | Abbreviation | Seat Relative to Button |
|----------|--------------|------------------------|
| Button | BTN | Has the button |
| Small Blind | SB | 1 seat left of button |
| Big Blind | BB | 2 seats left of button |
| Under the Gun | UTG | 3 seats left of button (first to act preflop) |
| UTG+1 | UTG+1 | 4 seats left of button |
| Cutoff | CO | 1 seat right of button (5 seats left) |

### 3.3 Position Adjustments by Player Count

| Players | Positions Used |
|---------|----------------|
| 6 | BTN, SB, BB, UTG, UTG+1, CO |
| 5 | BTN, SB, BB, UTG, CO |
| 4 | BTN, SB, BB, UTG |
| 3 | BTN, SB, BB |
| 2 (Heads-Up) | BTN/SB, BB (special rules apply - see Section 3.4) |

### 3.4 Heads-Up (2 Players) Special Rules

When only 2 players remain:
- The Button is ALSO the Small Blind
- The non-button player is the Big Blind
- **Preflop:** Button/SB acts FIRST
- **Postflop:** Button/SB acts LAST (BB acts first)

This is the only exception to normal position rules.

---

## 4. Blinds

### 4.1 Mandatory Blind Bets

Before cards are dealt, two players must post forced bets:
- **Small Blind (SB):** Posted by player immediately left of button
- **Big Blind (BB):** Posted by player two seats left of button; always exactly 2× the small blind

### 4.2 Blind Amounts

Blinds are defined by the current blind level:
```
Small Blind = Level-defined amount
Big Blind = 2 × Small Blind
```

Example blind levels:
| Level | Small Blind | Big Blind |
|-------|-------------|-----------|
| 1 | 10 | 20 |
| 2 | 15 | 30 |
| 3 | 25 | 50 |
| 4 | 50 | 100 |
| ... | ... | ... |

### 4.3 Antes

**Note: Antes are NOT applicable to this rulebook.**

Antes are additional forced bets from all players that are sometimes used in poker tournaments. In traditional poker:
- Antes are posted by all players before the deal, in addition to blinds
- They are commonly used in later tournament stages to increase action
- Typical ante amounts are 10-20% of the big blind

However, **this rulebook does not use antes**. Only small blind and big blind forced bets are used in this game.

### 4.4 Insufficient Chips for Blinds

If a player cannot afford the full blind:
- They post whatever chips they have remaining
- They are automatically all-in before the hand begins
- They can only win a pot proportional to their contribution (see Side Pots)

---

## 5. Dealing Procedure

### 5.1 Pre-Deal Setup

1. Button position is established
2. Small blind posts SB amount
3. Big blind posts BB amount

### 5.2 Hole Card Deal

1. Starting with player immediately left of button (Small Blind)
2. Deal one card face-down to each player, clockwise
3. Repeat for second card
4. Each player has exactly 2 hole cards

**Dealing Order:** SB → BB → UTG → ... → BTN (clockwise)

### 5.3 Community Card Deal

Community cards are dealt in three stages:

| Stage | Name | Cards Dealt | Total Community Cards |
|-------|------|-------------|----------------------|
| 1 | Flop | 3 cards | 3 |
| 2 | Turn | 1 card | 4 |
| 3 | River | 1 card | 5 |

### 5.4 Burn Cards

Before each community card deal:
- Remove ("burn") the top card of the deck face-down
- This card is out of play
- Then deal the community card(s)

**Burn sequence:**
1. Burn 1 → Deal Flop (3 cards)
2. Burn 1 → Deal Turn (1 card)
3. Burn 1 → Deal River (1 card)

---

## 6. Betting Rounds

### 6.1 The Four Betting Rounds

| Round | Name | When | Community Cards Visible |
|-------|------|------|------------------------|
| 1 | Preflop | After hole cards dealt | None |
| 2 | Flop | After flop dealt | 3 |
| 3 | Turn | After turn dealt | 4 |
| 4 | River | After river dealt | 5 |

### 6.2 Betting Order

**Preflop:**
- First to act: UTG (first player left of Big Blind)
- Last to act: Big Blind
- Order: UTG → UTG+1 → ... → BTN → SB → BB

**Postflop (Flop, Turn, River):**
- First to act: First active player left of button
- Last to act: Button (or nearest active player)
- Order: SB → BB → UTG → ... → BTN

### 6.3 When a Betting Round Ends

A betting round ends when:
1. All players except one have folded (hand ends immediately), OR
2. All remaining players have either:
   - Matched the current bet AND
   - Had at least one opportunity to act (or are all-in)

### 6.4 Betting Round Closure Conditions

The round is complete when action returns to the last aggressor (player who made the last bet/raise) and all other players have called, folded, or are all-in.

**Special Case - No Bet Made:**
If no one bets and everyone checks, the round ends when the last player to act checks.

**Special Case - Big Blind Preflop:**
If no one raises preflop and action comes back to BB, the BB has the "option" - they may check OR raise. The round doesn't end until BB acts.

---

## 7. Player Actions

### 7.1 Available Actions

| Action | Definition | When Available |
|--------|------------|----------------|
| **Fold** | Surrender cards, forfeit any claim to pot | Any time it's your turn |
| **Check** | Pass action without betting | Only when no bet is facing you |
| **Call** | Match the current bet exactly | When a bet is facing you |
| **Bet** | Put chips in when no one has bet this round | Only when no current bet exists |
| **Raise** | Increase the current bet | When a bet is facing you |
| **All-In** | Bet or call with all remaining chips | Any time (special rules apply) |

### 7.2 Action Hierarchy

When facing a bet, valid actions are:
- Fold
- Call (if you have enough chips)
- Raise (if raise is legal and you have enough chips)
- All-In (always available)

When NOT facing a bet:
- Check
- Bet
- All-In

### 7.3 Fold

- Player discards their hole cards
- Player forfeits all claim to current pot(s)
- Player cannot act again this hand
- Folded cards are NOT revealed to other players

### 7.4 Check

- Only valid when no bet faces the player
- Passes action to next player
- Player retains right to call or raise if someone bets after them

### 7.5 Call

- Player adds chips equal to: (current bet - amount already contributed this round)
- This matches the current highest bet
- Example: Bet is 100, you've put in 50 → Call amount is 50

### 7.6 Bet

- Only valid when no one has bet this round (current bet = 0)
- Player puts chips into the pot
- Minimum bet = Big Blind amount
- Maximum bet = All of player's chips (no limit)

### 7.7 Raise

- Valid when facing an existing bet
- Must increase the bet by at least the size of the previous raise (see Section 8)
- Exception: All-in for less (see Section 8.3)

### 7.8 All-In

- Player bets or calls with all remaining chips
- Player can still win the pot (or a portion via side pots)
- Player cannot take further action in the hand
- If all-in amount is less than a full call, special rules apply (Section 9)

### 7.9 Action Availability Conditions

This section defines the precise conditions that must be met for each action to be available. Understanding these conditions is critical for proper game implementation.

#### 7.9.1 State Variables Required

To determine available actions, track these state variables:

| Variable | Definition |
|----------|------------|
| `player_stack` | Player's total remaining chips |
| `player_current_bet` | Amount player has contributed this betting round |
| `round_current_bet` | Highest bet amount in the current betting round |
| `last_raise_size` | Size of the most recent raise in this round |
| `big_blind` | Current big blind amount |
| `player_is_active` | Player has not folded and is not all-in |
| `round_has_bet` | Whether any bet has been made this round |

#### 7.9.2 FOLD Conditions

**Availability:** Always available when it is the player's turn to act.

**Requirements:**
- Player is active (has not previously folded)
- Player is not already all-in from a prior action in the hand
- It is the player's turn in the action sequence

**Constraints:** None

**Notes:**
- Fold is always a legal action regardless of chip count, betting state, or round
- Once folded, player cannot take further actions in the hand
- Folded players forfeit all claims to any pot (main pot and all side pots)

#### 7.9.3 CHECK Conditions

**Availability:** Only when no outstanding bet faces the player.

**Requirements:**
```
player_current_bet == round_current_bet
AND round_current_bet >= 0
```

**Specific Cases:**

1. **Fresh Betting Round (No Bets Yet):**
   - `round_current_bet = 0`
   - `player_current_bet = 0`
   - CHECK is available

2. **After Everyone Checks:**
   - All prior players checked
   - `round_current_bet = 0`
   - CHECK is available

3. **Player Already Matched Current Bet:**
   - This occurs when action returns to a player who posted a blind and no one raised
   - Example: Preflop, Big Blind posted 50, everyone limped, action back to BB
   - BB can CHECK (their 50 matches the current bet of 50)

**Cannot Check When:**
- `player_current_bet < round_current_bet` (a bet is facing you)
- Someone has bet or raised and you haven't matched it

**Chip Requirements:** None (checking requires no chips)

**Notes:**
- Checking passes action but keeps player active in the hand
- Player may still face a bet from subsequent players in the round
- In heads-up, Big Blind has the "option" preflop if Small Blind just calls (can check or raise)

#### 7.9.4 CALL Conditions

**Availability:** When a bet is facing the player.

**Requirements:**
```
player_current_bet < round_current_bet
AND round_current_bet > 0
```

**Chip Scenarios:**

1. **Sufficient Chips for Full Call:**
   ```
   call_amount = round_current_bet - player_current_bet
   IF player_stack >= call_amount:
       CALL is available (full call)
   ```

2. **Insufficient Chips (Short Call → All-In):**
   ```
   IF player_stack < call_amount:
       Player can still CALL
       This becomes an all-in call for player_stack amount
       Side pot rules apply (Section 9)
   ```

**Cannot Call When:**
- `player_current_bet == round_current_bet` (no bet facing you; use CHECK)
- `round_current_bet == 0` (no one has bet; use CHECK or BET)

**Examples:**

| Scenario | player_current_bet | round_current_bet | call_amount | Action |
|----------|-------------------|-------------------|-------------|---------|
| Facing a bet | 0 | 100 | 100 | CALL for 100 |
| Facing a raise | 50 | 150 | 100 | CALL for 100 more |
| Already matched | 200 | 200 | 0 | Cannot CALL (use CHECK) |
| Short stack | 0 (stack=60) | 100 | 60 | CALL all-in for 60 |

**Notes:**
- Calling matches the current bet but does not increase it
- If calling with insufficient chips, player goes all-in (see Section 7.8)
- All-in call for less than full amount does not reopen betting to players who have already acted

#### 7.9.5 BET Conditions

**Availability:** Only when no bet has been made in the current betting round.

**Requirements:**
```
round_current_bet == 0
AND player_is_active == true
```

**Minimum Bet Calculation:**
```
minimum_bet = big_blind
```

**Chip Scenarios:**

1. **Sufficient Chips for Minimum Bet:**
   ```
   IF player_stack >= minimum_bet:
       BET is available
       Valid bet range: [minimum_bet, player_stack]
   ```

2. **Insufficient Chips for Minimum:**
   ```
   IF player_stack < minimum_bet:
       BET is still available (as all-in)
       Player bets all remaining chips
   ```

**Maximum Bet:**
```
maximum_bet = player_stack
```
(No-Limit: can bet entire stack)

**Cannot Bet When:**
- `round_current_bet > 0` (someone has already bet; use RAISE instead)
- Someone has already bet or raised this round

**Valid Bet Amounts:**
```
IF player_stack >= minimum_bet:
    valid_bet_range = [minimum_bet, player_stack]
ELSE:
    valid_bet_range = [player_stack] (all-in only)
```

**Examples:**

| Scenario | round_current_bet | big_blind | player_stack | Available Action |
|----------|-------------------|-----------|--------------|------------------|
| Fresh round | 0 | 50 | 500 | BET [50, 500] |
| After checks | 0 | 50 | 500 | BET [50, 500] |
| After bet | 100 | 50 | 500 | Cannot BET (use RAISE) |
| Short stack | 0 | 50 | 30 | BET 30 (all-in) |

**Notes:**
- BET initiates betting in a round where no bet exists
- The first bet in a round is effectively a "raise from zero"
- Minimum bet is always the big blind amount (not previous round's bet)
- Betting opens action to all remaining players

#### 7.9.6 RAISE Conditions

**Availability:** When facing a bet and player wishes to increase it.

**Requirements:**
```
round_current_bet > 0
AND player_current_bet < round_current_bet
AND player_is_active == true
```

**Minimum Raise Calculation:**
```
# The size of the last raise in this round
IF last_raise_size exists:
    minimum_raise_size = max(last_raise_size, big_blind)
ELSE:
    # First bet of round (bet is treated as a raise from 0)
    minimum_raise_size = max(round_current_bet, big_blind)

minimum_raise_to = round_current_bet + minimum_raise_size
```

**Chip Scenarios:**

1. **Sufficient Chips for Minimum Raise:**
   ```
   total_cost = minimum_raise_to - player_current_bet
   
   IF player_stack >= total_cost:
       RAISE is available
       Valid raise range: [minimum_raise_to, player_stack + player_current_bet]
   ```

2. **Insufficient Chips for Minimum Raise (All-In Raise):**
   ```
   IF player_stack < total_cost:
       Player can go ALL-IN
       total_amount = player_current_bet + player_stack
       
       IF total_amount >= minimum_raise_to:
           This is a legal RAISE (reopens betting)
       ELSE:
           This is treated as a CALL (does not reopen betting)
           See Section 8.3 for details
   ```

**Maximum Raise:**
```
maximum_raise_to = player_current_bet + player_stack
```
(No-Limit: can raise to entire stack)

**Cannot Raise When:**
- `round_current_bet == 0` (no bet exists; use BET instead)
- Player has insufficient chips even for all-in (but can still CALL or FOLD)

**Raise Amount Validation:**
```
# Player wants to raise to X
raise_to_amount = X
additional_cost = raise_to_amount - player_current_bet

# Validation checks:
1. raise_to_amount >= minimum_raise_to (unless all-in)
2. additional_cost <= player_stack
3. raise_to_amount > round_current_bet (must actually increase bet)
```

**Examples:**

| Scenario | Big Blind | Current Bet | Last Raise | Player Bet | Player Stack | Min Raise To | Action Available |
|----------|-----------|-------------|------------|------------|--------------|--------------|------------------|
| Initial raise | 50 | 50 | 50 | 0 | 500 | 100 | RAISE [100, 500] |
| Re-raise | 50 | 150 | 100 | 0 | 500 | 250 | RAISE [250, 500] |
| 3-bet | 50 | 500 | 350 | 0 | 1000 | 850 | RAISE [850, 1000] |
| Already called | 50 | 200 | 100 | 200 | 300 | 300 | Cannot RAISE (CHECK) |
| Short raise | 50 | 200 | 100 | 0 | 250 | 300 | ALL-IN 250 (call) |
| Exactly min | 50 | 200 | 100 | 0 | 300 | 300 | RAISE to 300 or ALL-IN |

**Detailed Example:**
```
Blinds: 25/50
- Player A bets 50 (last_raise_size = 50)
- Player B raises to 150 (last_raise_size = 100, the raise was 100)
- Player C wants to raise:
  - minimum_raise_size = max(100, 50) = 100
  - minimum_raise_to = 150 + 100 = 250
  - If Player C has 300 chips:
    - Can raise to [250, 300]
    - If raises to 250, next player's minimum is 250 + 100 = 350
    - If raises to 300 (all-in for 50 more than minimum):
      - Next player minimum is still 350 (based on 100 raise size)
```

**Notes:**
- Minimum raise size is based on the LAST raise in the current round, not the current total bet
- This prevents "nuisance raises" (small re-raises)
- All-in for less than minimum raise is treated as a call and does NOT reopen betting
- All-in that meets or exceeds minimum raise DOES reopen betting (see Section 8.3)

#### 7.9.7 ALL-IN Conditions

**Availability:** Always available when it is the player's turn to act.

**Requirements:**
- Player is active
- Player has at least 1 chip
- It is player's turn

**Constraints:** None (can always go all-in)

**Effect:**
```
all_in_amount = player_stack (all remaining chips)
total_committed = player_current_bet + all_in_amount
```

**All-In Functions As:**

1. **All-In as BET:**
   ```
   IF round_current_bet == 0:
       Bet all remaining chips
       Minimum bet rules don't apply when all-in
   ```

2. **All-In as CALL:**
   ```
   IF player_stack < (round_current_bet - player_current_bet):
       Call with all chips (partial call)
       Side pot created
       Does NOT reopen betting
   ```

3. **All-In as RAISE:**
   ```
   IF player_stack >= (round_current_bet - player_current_bet):
       total_committed = player_current_bet + player_stack
       
       IF total_committed >= minimum_raise_to:
           This is a legal RAISE (reopens betting)
       ELSE:
           Treated as CALL (does not reopen betting)
   ```

**Reopening Betting (Critical Rule):**
```
# After an all-in, determine if betting is reopened
all_in_total = player_current_bet + player_stack
raise_amount = all_in_total - round_current_bet

IF raise_amount >= minimum_raise_size:
    betting_reopened = true  # Players who already acted can re-raise
ELSE:
    betting_reopened = false  # Treated as call, no reopening
```

**Examples:**

| Scenario | Current Bet | Player Has Bet | Player Stack | All-In Total | Minimum Raise | Effect |
|----------|-------------|----------------|--------------|--------------|---------------|---------|
| Fresh round | 0 | 0 | 30 | 30 | 50 | BET 30 (all-in) |
| Facing bet | 100 | 0 | 60 | 60 | 200 | CALL 60 (partial) |
| Facing bet | 100 | 0 | 150 | 150 | 200 | CALL 150 (partial) |
| Facing bet | 100 | 0 | 220 | 220 | 200 | RAISE to 220 (reopens) |
| After calling | 200 | 200 | 300 | 500 | 400 | RAISE to 500 (reopens) |

**Notes:**
- All-in is ALWAYS a legal action regardless of other constraints
- All-in for less than minimum bet/raise is allowed but has specific effects
- Player going all-in cannot act again in the hand
- All-in player is still eligible to win pot(s) up to their contribution
- Multiple all-ins create side pots (see Section 9)

#### 7.9.8 Preflop vs. Postflop Considerations

The availability conditions above apply to ALL betting rounds, but certain nuances exist:

**Preflop Specifics:**

1. **Big Blind Option:**
   ```
   IF no_raises_occurred AND action_back_to_big_blind:
       Big blind has "option"
       Can CHECK (round ends) or RAISE (action continues)
       Big blind's initial forced bet counts as player_current_bet
   ```

2. **Small Blind:**
   ```
   Small blind treats their forced bet as player_current_bet
   To CALL the big blind, they add the difference
   ```

3. **Blind Posted = Current Bet:**
   ```
   Big Blind: player_current_bet = big_blind amount
   When no raises: round_current_bet = big_blind amount
   BB can CHECK because player_current_bet == round_current_bet
   ```

**Postflop Specifics:**

1. **Fresh Betting Round:**
   ```
   Each new street (flop, turn, river):
   - player_current_bet resets to 0 for all players
   - round_current_bet resets to 0
   - First action: CHECK or BET available
   ```

2. **No Blind Considerations:**
   - Postflop, no forced bets exist
   - round_current_bet starts at 0
   - CHECK is available to first actor

**Heads-Up Specifics:**

- Preflop: Button/Small Blind acts FIRST
- Postflop: Button acts LAST (Big Blind acts first)
- Same action availability rules apply
- Position change affects action order only, not availability

**Example: Preflop Big Blind Option**
```
Blinds: 50/100
- UTG: CALL 100
- CO: CALL 100  
- BTN: CALL 100
- SB: CALL 100 (adds 50 more)
- BB: player_current_bet = 100, round_current_bet = 100
       → Can CHECK (ends round) or RAISE (continues action)
```

#### 7.9.9 Action Availability Summary Table

| Action | Primary Condition | Chip Requirement | Can Go All-In |
|--------|------------------|------------------|---------------|
| **FOLD** | Always (when active) | None | N/A |
| **CHECK** | `player_current_bet == round_current_bet` | None | N/A |
| **CALL** | `player_current_bet < round_current_bet` | Any amount | Yes (partial call) |
| **BET** | `round_current_bet == 0` | ≥ big_blind (or all-in) | Yes |
| **RAISE** | `player_current_bet < round_current_bet` | ≥ minimum raise (or all-in) | Yes (see 8.3) |
| **ALL-IN** | Always (when active) | ≥ 1 chip | Yes (itself) |

#### 7.9.10 Decision Tree for Action Availability

```
START: Is it player's turn?
│
├─ NO → Wait
│
└─ YES → Is player active (not folded, not already all-in)?
    │
    ├─ NO → Skip turn
    │
    └─ YES → Determine available actions:
        │
        ├─ FOLD: Always available
        │
        ├─ ALL-IN: Always available
        │
        └─ Check betting state:
            │
            ├─ IF round_current_bet == 0:
            │   ├─ CHECK: Available
            │   └─ BET: Available (min = big_blind)
            │
            └─ IF round_current_bet > 0:
                │
                ├─ IF player_current_bet == round_current_bet:
                │   └─ CHECK: Available (already matched)
                │
                └─ IF player_current_bet < round_current_bet:
                    ├─ CALL: Available
                    └─ RAISE: Available (min = current + last_raise_size)
```


---

## 8. Betting Rules and Constraints

### 8.1 Minimum Bet

- The minimum bet (when no bet exists) = 1 Big Blind
- If player has fewer chips than minimum, they may still go all-in

### 8.2 Minimum Raise

The minimum raise amount is the greater of:
1. The Big Blind, OR
2. The size of the previous bet or raise in this round

**Calculation:**
```
Minimum Raise To = Current Bet + Last Raise Size
```

**Example:**
- Blinds 25/50
- Player A bets 50 (initial bet = BB)
- Player B minimum raise = 100 (50 + 50)
- Player C minimum raise = 150 (100 + 50... the "last raise" was 50)
- Player D raises to 300 (raise of 200)
- Player E minimum raise = 500 (300 + 200)

### 8.3 All-In for Less Than Minimum Raise

If a player goes all-in for less than a full raise:
- It is treated as a call, not a raise
- It does NOT reopen betting to players who have already acted
- Exception: It DOES reopen betting if it completes to a full raise

**Example:**
- Blinds 25/50, all players have acted
- Current bet: 200
- Last raise size: 100 (someone raised from 100 to 200)
- Player X goes all-in for 230 (only 30 more than current bet)
- This is NOT a legal raise (minimum would be 300)
- Players who already called 200 cannot re-raise
- Player X can still win proportionally

**Reopening Exception:**
- If all-in at least completes the minimum raise, it DOES reopen action
- Current bet 200, last raise 100 → minimum to reopen is 300
- All-in for 310 → action is reopened to all players

### 8.4 Maximum Bet

- No-Limit: No maximum; any amount up to total chip stack
- "All-in" is always a valid action

### 8.5 Raise Limits Per Round

- There is NO limit on the number of raises per betting round
- Betting continues until all players call, fold, or are all-in

### 8.6 Acting Out of Turn

In a software implementation:
- Prevent out-of-turn actions entirely
- Only the player whose turn it is can submit an action

---

## 9. All-In Situations and Side Pots

### 9.1 When All-In Occurs

A player is all-in when they have committed all their chips. This can happen:
1. Betting all chips
2. Calling with insufficient chips to match full bet
3. Raising with all chips
4. Posting blinds with insufficient chips

### 9.2 Main Pot and Side Pots

When a player is all-in for less than others are betting, side pots are created.

**Rule:** A player can only win from each opponent an amount equal to their own total investment.

### 9.3 Side Pot Calculation

**Step-by-step process:**

1. Identify the smallest all-in amount among all players in the hand
2. Create main pot: Each player contributes up to that amount
3. Remaining chips form side pot(s)
4. Repeat for each all-in level

**Example:**
- Player A: All-in for 100
- Player B: All-in for 300
- Player C: All-in for 500
- Player D: Calls 500

Pot breakdown:
| Pot | Contributions | Total | Eligible Players |
|-----|--------------|-------|------------------|
| Main Pot | 100 × 4 players | 400 | A, B, C, D |
| Side Pot 1 | 200 × 3 players (B,C,D) | 600 | B, C, D |
| Side Pot 2 | 200 × 2 players (C,D) | 400 | C, D |

### 9.4 Side Pot Awarding

At showdown:
1. Start with the last side pot created (smallest eligible group)
2. Best hand among ELIGIBLE players wins that pot
3. Move to next side pot, repeat
4. Finally, award main pot to best hand among ALL remaining players

### 9.5 Multiple All-Ins on Same Amount

If two players are all-in for the same amount:
- They both compete for the same pots
- No additional side pot is created between them

### 9.6 All-In with No Callers

If a player bets all-in and everyone folds:
- Player wins the pot immediately
- No showdown occurs
- Player does NOT reveal cards (unless they choose to)

---

## 10. Showdown

### 10.1 When Showdown Occurs

Showdown happens when:
1. The final betting round (river) is complete, AND
2. Two or more players remain (haven't folded)

**No Showdown:** If all players except one fold at any point, the remaining player wins immediately without showdown.

### 10.2 Showdown Order

Showdown follows a specific reveal order:

**If there was betting on the river:**
1. Last aggressor (player who made final bet/raise) shows first
2. Then clockwise from that player

**If river was checked around:**
1. First active player left of button shows first
2. Then clockwise

### 10.3 Mandatory Show

In software implementation for integrity:
- ALL players who reach showdown MUST reveal their hands
- This is non-optional (no "muck without showing")
- Ensures full game auditability

### 10.4 Mucking (Discarding Without Showing)

**For this implementation:** Not applicable. All hands at showdown are revealed.

In live poker, a player may muck (concede) if they see they're beaten. For software/auditing purposes, always require revelation.

### 10.5 Reading the Board (Playing the Board)

A player may use:
- Both hole cards + 3 community cards
- One hole card + 4 community cards
- Zero hole cards + 5 community cards ("playing the board")

The software must determine the best 5-card hand from the 7 available cards.

---

## 11. Hand Rankings

### 11.1 Hand Rank Hierarchy (Highest to Lowest)

| Rank | Hand | Description | Example |
|------|------|-------------|---------|
| 1 | **Royal Flush** | A-K-Q-J-10 of same suit | A♠ K♠ Q♠ J♠ 10♠ |
| 2 | **Straight Flush** | Five sequential cards of same suit | 7♥ 8♥ 9♥ 10♥ J♥ |
| 3 | **Four of a Kind** | Four cards of same rank | 9♠ 9♥ 9♦ 9♣ K♠ |
| 4 | **Full House** | Three of a kind + pair | K♠ K♥ K♦ 7♠ 7♣ |
| 5 | **Flush** | Five cards of same suit (not sequential) | A♦ J♦ 8♦ 4♦ 2♦ |
| 6 | **Straight** | Five sequential cards (mixed suits) | 5♣ 6♦ 7♠ 8♥ 9♣ |
| 7 | **Three of a Kind** | Three cards of same rank | 8♠ 8♥ 8♦ K♣ 3♠ |
| 8 | **Two Pair** | Two different pairs | A♠ A♣ 5♥ 5♦ K♠ |
| 9 | **One Pair** | Two cards of same rank | J♠ J♦ A♣ 8♥ 4♠ |
| 10 | **High Card** | No made hand; highest card plays | A♠ J♦ 9♣ 6♥ 3♠ |

### 11.2 Comparing Same-Ranked Hands

When players have the same hand rank, use these tiebreakers:

**Royal Flush:**
- Cannot tie (only one possible per suit)
- If board shows royal flush, all remaining players split

**Straight Flush:**
- Higher top card wins
- A-2-3-4-5 is lowest straight flush (5-high)

**Four of a Kind:**
- Higher quad rank wins
- If same (only possible with community quads), higher kicker wins

**Full House:**
- Higher three-of-a-kind wins
- If same trips, higher pair wins

**Flush:**
- Compare highest card, then second-highest, etc.
- Suit does NOT matter for comparison

**Straight:**
- Higher top card wins
- A-2-3-4-5 is lowest straight (5-high, "the wheel")
- A-K-Q-J-10 is highest (Broadway)
- NOTE: A-K-Q-J-10 and 2-3-4-5-A cannot both exist as straights (Ace is high OR low, not both simultaneously)

**Three of a Kind:**
- Higher trip rank wins
- If same, compare kickers (highest, then next)

**Two Pair:**
- Higher top pair wins
- If same, higher second pair wins
- If same, higher kicker wins

**One Pair:**
- Higher pair wins
- If same, compare kickers in descending order

**High Card:**
- Compare highest card, then second, third, fourth, fifth

### 11.3 Kickers

A "kicker" is a card not part of the primary hand that breaks ties.

**Kicker Rules:**
- Only 5 cards play - extra cards beyond 5 are irrelevant
- Compare kickers only after primary hand is tied
- Compare in descending order until difference found

**Example:**
- Player A: A♠ K♣ (with board 8♥ 8♦ 3♣ 5♠ 2♦) → Pair of 8s, A-K-5 kickers
- Player B: A♦ Q♥ (same board) → Pair of 8s, A-Q-5 kickers
- Player A wins (K kicker beats Q kicker)

### 11.4 The Wheel (A-2-3-4-5)

- A-2-3-4-5 is a valid straight (called "the wheel")
- It is the LOWEST straight (5-high)
- 6-5-4-3-2 beats A-2-3-4-5
- The Ace functions as a 1 ONLY in this specific straight

### 11.5 Wrap-Around Straights

These are NOT valid:
- K-A-2-3-4 (NOT a straight)
- Q-K-A-2-3 (NOT a straight)

Ace can only be high (above King) or low (below 2), never both.

### 11.6 Flush Suit Irrelevance

- Suits NEVER break ties
- A♠ K♠ Q♠ J♠ 9♠ equals A♥ K♥ Q♥ J♥ 9♥ (tie, split pot)
- This applies to all hand comparisons

---

## 12. Pot Award and Split Pots

### 12.1 Single Winner

If one player has the best hand:
- That player wins the entire pot (or the portion they're eligible for)
- Chips are added to their stack
- Hand ends

### 12.2 Split Pot (Tie)

If two or more players have exactly equal hands:
- Pot is divided equally among them
- If pot cannot be divided evenly, see Section 12.3

### 12.3 Odd Chip Rule

When a pot cannot be evenly divided:
1. Divide as evenly as possible
2. Remaining odd chip(s) go to:
   - **First player left of the button** among the tied winners

**Example:**
- Pot: 150 chips
- Three-way tie
- Each player gets 50 chips (150 ÷ 3 = 50, no remainder)

**Example with remainder:**
- Pot: 155 chips
- Three-way tie
- 155 ÷ 3 = 51 remainder 2
- Two players closest left of button get 52 each, third gets 51

### 12.4 Side Pot Distribution

When multiple pots exist:
1. Award smallest side pot first (fewest eligible players)
2. Continue to larger pots
3. Award main pot last

A player eliminated before showdown (folded) is not eligible for any pot.

### 12.5 Folded Players

- Folded players win nothing
- Their contributed chips remain in the pot for others

### 12.6 Uncalled Bet Returns

When a player bets or raises and not all players can match the full amount (due to all-in situations), the uncalled portion of the bet must be returned to the bettor.

**Rules:**
1. Only the portion that cannot be matched by any player is returned
2. Return happens before pot calculation
3. Returned chips are NOT part of any pot
4. Returned chips go directly back to the bettor's stack

**Example:**
- Player A bets 500
- Player B calls 500
- Player C can only call 200 (all-in for 200)
- Player A's uncalled portion: 500 - 200 = 300
- Player A receives 300 back immediately
- Pot contains: 200 (from A) + 200 (from B) + 200 (from C) = 600

**Example with multiple all-ins:**
- Player A bets 1000
- Player B calls 1000
- Player C all-in for 300
- Player D all-in for 500
- Uncalled portion for A: 1000 - 500 = 500 (lowest all-in is 300, but D's 500 is the effective cap)
- Uncalled portion for B: 1000 - 500 = 500
- Pot contains: 500 (from A) + 500 (from B) + 300 (from C) + 500 (from D) = 1800
- A and B each receive 500 back

**Special Case - Everyone Folds:**
- If a player bets and everyone folds, the bettor wins the entire pot
- No uncalled bet return occurs (they win the pot instead)

---

## 13. Player Elimination

### 13.1 When Elimination Occurs

A player is eliminated when:
- They have zero chips remaining after a hand is complete
- A player is never eliminated mid-hand

### 13.2 Elimination Process

1. Hand completes (showdown or all fold)
2. Pot(s) are awarded
3. Any player with 0 chips is eliminated
4. Eliminated player receives their finish position
5. If multiple players eliminated same hand, see Section 13.3

### 13.3 Simultaneous Elimination

If multiple players bust on the same hand:
- Player who started the hand with MORE chips finishes higher
- If exact same starting stack, they tie for position (split payout)

**Example:**
- 3 players remain
- Player A (500 chips) and Player B (300 chips) both lose all-in to Player C
- Player B finishes 3rd (had fewer chips)
- Player A finishes 2nd (had more chips)
- Player C finishes 1st

### 13.4 Position After Elimination

- When a player is eliminated, their seat is empty
- Button continues to rotate as normal
- Blinds continue to rotate, skipping empty seats

---

## 14. Button and Blind Movement

### 14.1 Initial Button Assignment

At the start of a tournament or when a new table begins:

1. **High Card Draw:**
   - Each player receives one card face-up from a shuffled deck
   - The player with the highest card receives the first dealer button
   - Card ranking: Ace (high) > King > Queen > Jack > 10 > 9 > 8 > 7 > 6 > 5 > 4 > 3 > 2

2. **Tiebreaker:**
   - If multiple players have the same rank, suits break the tie
   - Suit order (highest to lowest): Spades (♠) > Hearts (♥) > Diamonds (♦) > Clubs (♣)
   - Example: Ace of Spades beats Ace of Hearts

3. **After Initial Assignment:**
   - Once the button is assigned via high card draw, it rotates clockwise after each hand
   - All subsequent button movement follows Section 14.2

**When This Applies:**
- At the start of the tournament (first hand)
- When a new table begins play
- When starting a new button/blind game

### 14.2 Standard Button Movement

After each hand:
- Button moves one position clockwise
- Skips eliminated players (empty seats)
- Small blind is left of button
- Big blind is left of small blind

### 14.3 Dead Button Rule

If the player in small blind position is eliminated:
- Button can move to the empty seat (dead button)
- OR button can skip to next active player

**For simplicity:** Always skip eliminated positions. Button moves to next active player.

### 14.4 Heads-Up Transition

When transitioning from 3 players to 2 (heads-up):
- Player who had the button retains it (if still in)
- Otherwise, button moves as normal
- Apply heads-up rules from Section 3.4

### 14.5 Blind Responsibility

- A player can never post both blinds
- If this situation would arise, adjust button position

---

## 15. Tournament Progression

### 15.1 Blind Level Increases

- Blinds increase at regular intervals (time or hands)
- Increase schedule is predetermined
- Increases create pressure to play, preventing stalling

### 15.2 Example Blind Structure

| Level | Small Blind | Big Blind | Duration |
|-------|-------------|-----------|----------|
| 1 | 10 | 20 | 10 hands |
| 2 | 15 | 30 | 10 hands |
| 3 | 25 | 50 | 10 hands |
| 4 | 50 | 100 | 10 hands |
| 5 | 75 | 150 | 10 hands |
| 6 | 100 | 200 | 10 hands |
| 7 | 150 | 300 | 10 hands |
| 8 | 200 | 400 | 10 hands |
| 9 | 300 | 600 | 10 hands |
| 10 | 500 | 1000 | Until end |

### 15.3 Short Stack Management

As blinds increase, some players become "short stacked":
- Short stack = less than 10-15 big blinds
- Increases pressure and all-in frequency
- Natural tournament pressure mechanism

---

## 16. End Conditions

### 16.1 Tournament Winner

The tournament ends when one player has all chips:
- That player is the winner (1st place)
- All other players have been eliminated

### 16.2 Prize Distribution

Prizes are awarded based on finish position:
- 1st place: Winner's share per payout structure
- 2nd place: Runner-up share
- Etc.

**Chip count at end is irrelevant** - only finish order matters.

### 16.3 Final Hand

The final hand plays out normally:
- No special rules apply
- Loser is eliminated, winner takes all chips
- Tournament complete

---

## 17. Complete Hand Example

### 17.1 Setup

- 4 players: Alice (BTN, 1000), Bob (SB, 800), Charlie (BB, 1200), Diana (UTG, 1000)
- Blinds: 25/50
- Alice has the button

### 17.2 Pre-Deal

1. Bob posts SB: 25
2. Charlie posts BB: 50

**Pot: 75**

### 17.3 Dealing

Hole cards dealt:
- Bob (SB): 7♠ 2♦
- Charlie (BB): A♥ K♣
- Diana (UTG): Q♠ Q♦
- Alice (BTN): 9♣ 8♣

### 17.4 Preflop Betting

Action starts with Diana (UTG):
1. Diana: Raises to 150
2. Alice: Calls 150
3. Bob: Folds (loses 25 already posted)
4. Charlie: Calls 150 (adds 100 more)

**Pot: 475** (150×3 + 25 from Bob's folded SB)

### 17.5 Flop

Burn one card, deal flop: Q♣ 7♣ 2♣

1. Charlie (first active left of button): Checks
2. Diana: Bets 200
3. Alice: Raises to 500
4. Charlie: Folds
5. Diana: Calls 500 (adds 300 more)

**Pot: 1475**

### 17.6 Turn

Burn one card, deal turn: K♠

Board: Q♣ 7♣ 2♣ K♠

1. Diana: Checks
2. Alice: Bets 350 (all-in)

Diana considers:
- She has set of Queens (Q♠ Q♦ with Q♣ on board)
- Alice could have flush (three clubs on board) or be bluffing
- Diana has 350 remaining

3. Diana: Calls 350 (all-in)

Both players all-in. **Pot: 2175**

### 17.7 River

Burn one card, deal river: 4♥

Final board: Q♣ 7♣ 2♣ K♠ 4♥

### 17.8 Showdown

Both players reveal:
- Diana: Q♠ Q♦ → Three Queens (Q-Q-Q-K-7)
- Alice: 9♣ 8♣ → Flush (Q-9-8-7-2 of clubs)

**Winner: Alice** (Flush beats Three of a Kind)

### 17.9 Pot Award

- Alice wins entire pot: 2175
- Alice's new stack: 2175
- Diana is eliminated (0 chips)

### 17.10 Post-Hand

Remaining players:
- Alice: 2175
- Bob: 775
- Charlie: 1050

Button moves to Bob for next hand.

---

## 18. Edge Cases Reference

### 18.1 All-In Before Cards Dealt

If a player's chips are less than or equal to their required blind:
- They post all remaining chips
- They are all-in from the start
- Main pot is calculated accordingly

### 18.2 All Players All-In

If all remaining players are all-in:
- All remaining community cards are dealt
- No further betting occurs
- Showdown determines winner

### 18.3 Big Blind All-In for Less

If BB can only post partial big blind:
- They post all chips as BB
- Other players see reduced effective BB
- Minimum raise is still based on full BB amount

### 18.4 Everyone Folds to Big Blind

If all players fold to the BB (preflop):
- BB wins the pot (SB + BB)
- No showdown occurs
- BB does not reveal cards

### 18.5 Heads-Up Blind All-In

In heads-up, if button/SB posts all chips as blind:
- They are all-in
- BB can call, raise, or fold
- If BB folds, button/SB wins BB

### 18.6 Chopped Board

If the best 5-card hand IS the community cards:
- All remaining players "play the board"
- Pot is split equally among them
- Hole cards are irrelevant

**Example:** Board is A♠ A♣ K♥ K♦ Q♠ (two pair, A-A-K-K-Q)
- Player 1 holds: 7♦ 3♣
- Player 2 holds: 9♥ 5♠
- Both play the board, pot is split

### 18.7 Three-or-More-Way Tie

Split pot equally:
- Use odd chip rule for remainders
- Order of odd chips: clockwise from button

### 18.8 Raise to Less Than Double

When a player wants to raise but has less than double the current bet:
- They may go all-in for whatever they have
- This may or may not reopen betting (see Section 8.3)

### 18.9 Only One Player with Chips

If only one player has chips and others are all-in:
- That player cannot bet
- All remaining cards are dealt
- Showdown occurs normally

### 18.10 Empty Seat on Blind

If the seat due for blind is empty (eliminated player):
- Blind skips to next active player
- Button adjusts accordingly

---

## 19. Glossary

| Term | Definition |
|------|------------|
| **All-In** | Betting all remaining chips |
| **Big Blind (BB)** | Larger forced bet; posted by player two left of button |
| **Board** | The community cards |
| **Button (BTN)** | Dealer position marker; best position postflop |
| **Call** | Match the current bet |
| **Check** | Pass without betting (only when no bet faces you) |
| **Community Cards** | Five shared cards dealt face-up |
| **Cutoff (CO)** | Position one right of button |
| **Flop** | First three community cards |
| **Fold** | Surrender hand, forfeit pot |
| **Heads-Up** | Two players remaining |
| **Hole Cards** | Two private cards dealt to each player |
| **Kicker** | Side card used to break ties |
| **Limp** | Calling the big blind preflop (no raise) |
| **Main Pot** | Primary pot all players are eligible for |
| **Muck** | Fold without showing cards |
| **No-Limit** | No maximum bet |
| **Nuts** | Best possible hand given the board |
| **Out** | Card that would improve your hand |
| **Pot** | Total chips wagered in current hand |
| **Preflop** | Betting round before community cards |
| **Raise** | Increase the current bet |
| **River** | Fifth and final community card |
| **Showdown** | Revealing hands to determine winner |
| **Side Pot** | Secondary pot when player is all-in for less |
| **Small Blind (SB)** | Smaller forced bet; posted by player left of button |
| **Stack** | Player's total chip count |
| **Turn** | Fourth community card |
| **Under the Gun (UTG)** | First position to act preflop |
| **Wheel** | A-2-3-4-5 straight (lowest) |

---

## Appendix A: Hand Ranking Quick Reference

```
1. Royal Flush     → A-K-Q-J-10 suited
2. Straight Flush  → Sequential suited (e.g., 5-6-7-8-9 suited)
3. Four of a Kind  → Quad (e.g., 8-8-8-8-x)
4. Full House      → Trips + Pair (e.g., K-K-K-7-7)
5. Flush           → Five suited non-sequential
6. Straight        → Five sequential (e.g., 4-5-6-7-8)
7. Three of a Kind → Trips (e.g., J-J-J-x-x)
8. Two Pair        → Two pairs (e.g., A-A-5-5-x)
9. One Pair        → Single pair (e.g., 9-9-x-x-x)
10. High Card      → Nothing; highest card plays
```

---

## Appendix B: Betting Round Summary

```
PREFLOP:
  - Hole cards dealt
  - Blinds posted
  - Action: UTG → ... → BTN → SB → BB
  - BB has option if no raise

FLOP:
  - Burn, deal 3 cards
  - Action: SB → BB → ... → BTN (first active left of button)

TURN:
  - Burn, deal 1 card
  - Action: Same as flop

RIVER:
  - Burn, deal 1 card
  - Action: Same as flop
  - Showdown if 2+ players remain
```

---

## Appendix C: Minimum Raise Calculation

```
Scenario: Determining minimum legal raise

Variables:
  - current_bet: The current bet to call
  - previous_raise_size: The size of the last raise in this round
  - big_blind: The big blind amount

Formula:
  minimum_raise_to = current_bet + max(previous_raise_size, big_blind)
  minimum_raise_size = minimum_raise_to - current_bet

Example:
  - Big blind: 50
  - Player A bets 50
    → current_bet = 50, previous_raise_size = 50 (initial bet = raise from 0)
  - Player B raises to 150
    → raise_size = 100 (150 - 50)
    → current_bet = 150, previous_raise_size = 100
  - Player C minimum raise:
    → minimum_raise_to = 150 + 100 = 250
```

---

## Appendix D: Side Pot Calculation Algorithm

```
Input: List of players with their total contributions

Algorithm:
1. Sort players by total contribution (ascending)
2. Initialize previous_level = 0
3. For each unique contribution level:
   a. Calculate pot_contribution = (level - previous_level) × eligible_players
   b. Create pot with that amount
   c. Mark pot as eligible for all players at or above this level
   d. previous_level = level
4. Return list of pots with eligibility

Example:
  Players: A(100), B(300), C(500), D(500)
  
  Level 100: (100 - 0) × 4 = 400 → Main Pot (A,B,C,D eligible)
  Level 300: (300 - 100) × 3 = 600 → Side Pot 1 (B,C,D eligible)
  Level 500: (500 - 300) × 2 = 400 → Side Pot 2 (C,D eligible)
```

---

## Appendix E: Showdown Winner Determination Algorithm

```
Input: List of players with their 7 cards each (2 hole + 5 community)

Algorithm:
1. For each player:
   a. Generate all 21 possible 5-card combinations
   b. Evaluate each combination's hand rank
   c. Store best hand for player
2. Compare all players' best hands:
   a. Group by hand rank (Royal Flush, etc.)
   b. Within same rank, apply tiebreaker rules
   c. Determine winner(s)
3. Award pot(s) to winner(s)

Hand Evaluation:
- Return tuple: (rank, [tiebreaker_values])
- Rank: 1 (Royal Flush) to 10 (High Card)
- Tiebreaker: Depends on hand type
  - Flush: [highest, second, third, fourth, fifth]
  - Full House: [trips_rank, pair_rank]
  - Etc.
```

---

*End of Rulebook*