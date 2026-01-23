# Texas Hold'em No-Limit Tournament Rules - Atomic Specification

> **Purpose:** Atomic, testable rule specifications for ClankerPoker engine
> **Format:** Each rule is independent and verifiable
> **Version:** 1.0

---

## Table of Contents

1. [Card System](#1-card-system)
2. [Deck System](#2-deck-system)
3. [Hand Evaluation](#3-hand-evaluation)
4. [Hand Comparison](#4-hand-comparison)
5. [Position System](#5-position-system)
6. [Blind System](#6-blind-system)
7. [Player State](#7-player-state)
8. [Action Validation](#8-action-validation)
9. [Bet Calculation](#9-bet-calculation)
10. [Pot Management](#10-pot-management)
11. [Side Pot System](#11-side-pot-system)
12. [Betting Round](#12-betting-round)
13. [Deal Progression](#13-deal-progression)
14. [Showdown](#14-showdown)
15. [Hand Lifecycle](#15-hand-lifecycle)
16. [Player Elimination](#16-player-elimination)
17. [Tournament Progression](#17-tournament-progression)
18. [Timeout Handling](#18-timeout-handling)

---

## 1. Card System

### 1.1 Card Structure

| Rule ID | Rule | Test |
|---------|------|------|
| CARD-001 | A card has exactly two properties: rank and suit | `Card(rank, suit)` is valid |
| CARD-002 | Valid ranks are: 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A | Reject any other rank |
| CARD-003 | Valid suits are: spades, hearts, diamonds, clubs | Reject any other suit |
| CARD-004 | A card is uniquely identified by rank + suit combination | `Card(A, spades) != Card(A, hearts)` |
| CARD-005 | Two cards with same rank and suit are equal | `Card(A, spades) == Card(A, spades)` |

### 1.2 Rank Ordering

| Rule ID | Rule | Test |
|---------|------|------|
| RANK-001 | Rank ordering low to high: 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A | `rank(2) < rank(3) < ... < rank(A)` |
| RANK-002 | Numeric rank values: 2=2, 3=3, ..., 10=10, J=11, Q=12, K=13, A=14 | `rank_value(J) == 11` |
| RANK-003 | Ace is the highest rank in standard comparison | `rank(A) > rank(K)` |
| RANK-004 | Ace can be low (value=1) ONLY in A-2-3-4-5 straight | Special case in straight detection |
| RANK-005 | Ace is NOT low in any other context | `A-2-3` is not a sequence outside straights |

### 1.3 Suit Properties

| Rule ID | Rule | Test |
|---------|------|------|
| SUIT-001 | All four suits are exactly equal in value | No suit beats another |
| SUIT-002 | Suits never break ties | Flush A♠ K♠ Q♠ J♠ 9♠ == A♥ K♥ Q♥ J♥ 9♥ |
| SUIT-003 | Suits are only used for flush detection | Same suit × 5 = flush |

---

## 2. Deck System

### 2.1 Deck Composition

| Rule ID | Rule | Test |
|---------|------|------|
| DECK-001 | A standard deck contains exactly 52 cards | `len(deck) == 52` |
| DECK-002 | Deck contains 13 cards of each suit | `count(spades) == 13` for each suit |
| DECK-003 | Deck contains 4 cards of each rank | `count(Aces) == 4` for each rank |
| DECK-004 | No duplicate cards exist in a deck | All 52 cards are unique |
| DECK-005 | A new deck is created for each hand | Previous hand's deck is discarded |

### 2.2 Deck Operations

| Rule ID | Rule | Test |
|---------|------|------|
| DECK-006 | Shuffle randomizes card order | Two shuffles produce different orders (probabilistic) |
| DECK-007 | Shuffle maintains all 52 cards | `len(shuffled_deck) == 52`, no duplicates |
| DECK-008 | Deal removes card from top of deck | After deal, deck has 51 cards |
| DECK-009 | Dealt cards are removed from deck | Cannot deal same card twice |
| DECK-010 | Burn discards top card face-down | Burned card is out of play |

### 2.3 Randomization Requirements

| Rule ID | Rule | Test |
|---------|------|------|
| RAND-001 | Shuffle must be cryptographically secure | Use CSPRNG |
| RAND-002 | Each card position equally likely | Statistical distribution test |
| RAND-003 | Shuffle seed must be unpredictable | No pattern in consecutive shuffles |

---

## 3. Hand Evaluation

### 3.1 Hand Ranking Hierarchy

| Rule ID | Rank | Hand | Definition | Test |
|---------|------|------|------------|------|
| HAND-001 | 1 | Royal Flush | A-K-Q-J-10 of same suit | Detect 10-J-Q-K-A suited |
| HAND-002 | 2 | Straight Flush | 5 sequential cards of same suit | Detect 5 consecutive suited |
| HAND-003 | 3 | Four of a Kind | 4 cards of same rank | Detect 4 matching ranks |
| HAND-004 | 4 | Full House | 3 of a kind + pair | Detect trips + pair |
| HAND-005 | 5 | Flush | 5 cards of same suit, not sequential | Detect 5 same suit |
| HAND-006 | 6 | Straight | 5 sequential cards, mixed suits | Detect 5 consecutive |
| HAND-007 | 7 | Three of a Kind | 3 cards of same rank | Detect 3 matching ranks |
| HAND-008 | 8 | Two Pair | 2 different pairs | Detect 2 distinct pairs |
| HAND-009 | 9 | One Pair | 2 cards of same rank | Detect 2 matching ranks |
| HAND-010 | 10 | High Card | No made hand | Default when nothing else |

### 3.2 Hand Ranking Order

| Rule ID | Rule | Test |
|---------|------|------|
| RANK-ORD-001 | Royal Flush beats Straight Flush | `royal_flush > straight_flush` |
| RANK-ORD-002 | Straight Flush beats Four of a Kind | `straight_flush > four_kind` |
| RANK-ORD-003 | Four of a Kind beats Full House | `four_kind > full_house` |
| RANK-ORD-004 | Full House beats Flush | `full_house > flush` |
| RANK-ORD-005 | Flush beats Straight | `flush > straight` |
| RANK-ORD-006 | Straight beats Three of a Kind | `straight > three_kind` |
| RANK-ORD-007 | Three of a Kind beats Two Pair | `three_kind > two_pair` |
| RANK-ORD-008 | Two Pair beats One Pair | `two_pair > one_pair` |
| RANK-ORD-009 | One Pair beats High Card | `one_pair > high_card` |

### 3.3 Best Hand Selection

| Rule ID | Rule | Test |
|---------|------|------|
| BEST-001 | Player has access to 7 cards (2 hole + 5 community) | Input: 7 cards |
| BEST-002 | Best hand is exactly 5 cards | Output: 5 cards |
| BEST-003 | Must evaluate all 21 combinations of 5 from 7 | C(7,5) = 21 combinations |
| BEST-004 | Return highest ranking combination | Compare all 21, return best |
| BEST-005 | Player may use 0, 1, or 2 hole cards | All combinations valid |
| BEST-006 | Playing the board: use 0 hole cards + 5 community | Valid scenario |

### 3.4 Straight Detection

| Rule ID | Rule | Test |
|---------|------|------|
| STR-001 | Straight requires 5 consecutive ranks | 5-6-7-8-9 is straight |
| STR-002 | A-2-3-4-5 is valid straight (wheel) | Ace low special case |
| STR-003 | 10-J-Q-K-A is valid straight (broadway) | Ace high case |
| STR-004 | K-A-2-3-4 is NOT a straight | No wrap-around |
| STR-005 | Q-K-A-2-3 is NOT a straight | No wrap-around |
| STR-006 | Wheel (A-2-3-4-5) is lowest straight | 2-3-4-5-6 beats wheel |
| STR-007 | Broadway (10-J-Q-K-A) is highest straight | Broadway beats K-high straight |
| STR-008 | Suits are irrelevant for straight | Mixed suits allowed |

### 3.5 Flush Detection

| Rule ID | Rule | Test |
|---------|------|------|
| FLU-001 | Flush requires 5 cards of same suit | 5 spades = flush |
| FLU-002 | Flush ranks are compared high to low | A-high flush beats K-high |
| FLU-003 | Suits do not determine flush winner | Spade flush = Heart flush if same ranks |
| FLU-004 | 6 or 7 same-suit cards: use best 5 | Take highest 5 of suited cards |

### 3.6 Full House Detection

| Rule ID | Rule | Test |
|---------|------|------|
| FH-001 | Full house = three of a kind + pair | K-K-K-7-7 = full house |
| FH-002 | If two trips possible, use higher trips | K-K-K-7-7-7-2: use K-K-K-7-7 |
| FH-003 | Trips rank determines full house rank | K-K-K-2-2 beats Q-Q-Q-A-A |

---

## 4. Hand Comparison

### 4.1 Same Rank Tiebreakers

| Rule ID | Hand | Tiebreaker Rule | Test |
|---------|------|-----------------|------|
| TIE-001 | Royal Flush | Always tie (split pot) | Same hand if same rank |
| TIE-002 | Straight Flush | Higher top card wins | 9-high SF beats 8-high SF |
| TIE-003 | Four of a Kind | Higher quad rank, then kicker | Q-Q-Q-Q-K beats Q-Q-Q-Q-J |
| TIE-004 | Full House | Higher trips, then higher pair | K-K-K-3-3 beats K-K-K-2-2 |
| TIE-005 | Flush | Compare ranks high to low | A-K-J-9-7 beats A-K-J-9-6 |
| TIE-006 | Straight | Higher top card wins | 9-high straight beats 8-high |
| TIE-007 | Three of a Kind | Higher trips, then kickers | Q-Q-Q-A-K beats Q-Q-Q-A-J |
| TIE-008 | Two Pair | Higher top pair, then second pair, then kicker | A-A-5-5-K beats A-A-5-5-Q |
| TIE-009 | One Pair | Higher pair, then kickers | K-K-A-Q-J beats K-K-A-Q-10 |
| TIE-010 | High Card | Compare all 5 cards high to low | A-K-Q-J-9 beats A-K-Q-J-8 |

### 4.2 Kicker Rules

| Rule ID | Rule | Test |
|---------|------|------|
| KICK-001 | Only 5 cards play - extra cards irrelevant | 6th, 7th cards ignored |
| KICK-002 | Kickers compared in descending order | Highest kicker first |
| KICK-003 | Kickers only matter when primary hand ties | Same pair → compare kickers |
| KICK-004 | Kicker comparison continues until difference found | May need all kickers |
| KICK-005 | All 5 cards identical = tie (split pot) | No tiebreaker possible |

### 4.3 Board Play Scenarios

| Rule ID | Rule | Test |
|---------|------|------|
| BOARD-001 | If board is best hand, all active players tie | Board: A-A-K-K-Q, players split |
| BOARD-002 | Player's hole cards only matter if they improve hand | Hole 2-3 with board A-A-K-K-Q = play board |
| BOARD-003 | At least one player may beat board | Hole A-x with board K-K-Q-Q-J beats board |

---

## 5. Position System

### 5.1 Button (Dealer)

| Rule ID | Rule | Test |
|---------|------|------|
| BTN-001 | Exactly one player has button each hand | `count(button) == 1` |
| BTN-002 | Button rotates clockwise after each hand | Next active player left |
| BTN-003 | Button skips eliminated players | Empty seats ignored |
| BTN-004 | Button determines all other positions | SB, BB relative to button |
| BTN-005 | Initial button assigned randomly at tournament start | Random first position |

### 5.2 Blind Positions

| Rule ID | Rule | Test |
|---------|------|------|
| POS-001 | Small Blind is first active player left of button | 1 seat clockwise from BTN |
| POS-002 | Big Blind is first active player left of small blind | 1 seat clockwise from SB |
| POS-003 | Blinds skip eliminated players | Only active players post |
| POS-004 | A player cannot post both blinds | Impossible scenario |

### 5.3 Standard Positions (3+ Players)

| Rule ID | Players | Positions (clockwise from button) | Test |
|---------|---------|-----------------------------------|------|
| POS-005 | 6 | BTN, SB, BB, UTG, UTG+1, CO | Verify order |
| POS-006 | 5 | BTN, SB, BB, UTG, CO | Verify order |
| POS-007 | 4 | BTN, SB, BB, UTG | Verify order |
| POS-008 | 3 | BTN, SB, BB | Verify order |

### 5.4 Heads-Up Special Rules (2 Players)

| Rule ID | Rule | Test |
|---------|------|------|
| HU-001 | Button is also Small Blind | BTN = SB |
| HU-002 | Non-button player is Big Blind | Other player = BB |
| HU-003 | Preflop: Button/SB acts FIRST | BTN/SB → BB |
| HU-004 | Postflop: Button/SB acts LAST | BB → BTN/SB |
| HU-005 | Heads-up rules apply when exactly 2 players remain | Transition from 3→2 |

### 5.5 Action Order - Preflop

| Rule ID | Rule | Test |
|---------|------|------|
| ACT-PRE-001 | First to act: UTG (first left of BB) | UTG starts preflop |
| ACT-PRE-002 | Action proceeds clockwise | UTG → UTG+1 → ... |
| ACT-PRE-003 | Button acts after CO (or last position before blinds) | BTN before blinds |
| ACT-PRE-004 | Small Blind acts after Button | SB second-to-last |
| ACT-PRE-005 | Big Blind acts last preflop | BB has final action |
| ACT-PRE-006 | Skip folded players | Folded = no action |
| ACT-PRE-007 | Skip all-in players | All-in = no action |

### 5.6 Action Order - Postflop

| Rule ID | Rule | Test |
|---------|------|------|
| ACT-POST-001 | First to act: first active player left of button | SB or next active |
| ACT-POST-002 | Action proceeds clockwise | Left of button → button |
| ACT-POST-003 | Button acts last (or nearest active player) | BTN has position |
| ACT-POST-004 | Skip folded players | Folded = no action |
| ACT-POST-005 | Skip all-in players | All-in = no action |

---

## 6. Blind System

### 6.1 Blind Structure

| Rule ID | Rule | Test |
|---------|------|------|
| BLI-001 | Small Blind = level-defined amount | SB from blind schedule |
| BLI-002 | Big Blind = 2 × Small Blind | BB = SB × 2 |
| BLI-003 | Blinds are posted before cards are dealt | Blinds first, then deal |
| BLI-004 | Blinds are forced bets (not optional) | Must post if in position |
| BLI-005 | Blind positions determined by button location | SB left of BTN, BB left of SB |

### 6.2 Posting Blinds

| Rule ID | Rule | Test |
|---------|------|------|
| POST-001 | SB player posts SB amount | Exact amount required |
| POST-002 | BB player posts BB amount | Exact amount required |
| POST-003 | Posted blinds go into pot | Pot starts with SB + BB |
| POST-004 | Blinds are live bets | Count toward player's investment |

### 6.3 Insufficient Chips for Blinds

| Rule ID | Rule | Test |
|---------|------|------|
| SHORT-001 | Player posts all remaining chips if less than required blind | All-in blind |
| SHORT-002 | Partial blind player is all-in before cards dealt | No further action possible |
| SHORT-003 | Partial blind creates side pot scenario | Main pot limited |
| SHORT-004 | Minimum raise still based on full BB amount | Not reduced by partial blind |

### 6.4 Blind Escalation

| Rule ID | Rule | Test |
|---------|------|------|
| ESC-001 | Blinds increase at predefined intervals | Per schedule |
| ESC-002 | Interval can be hand-based or time-based | X hands or Y minutes |
| ESC-003 | New blinds apply starting next hand | Current hand unaffected |
| ESC-004 | Blind schedule is fixed at tournament start | No changes mid-tournament |
| ESC-005 | All players informed when blinds increase | Notification required |

### 6.5 Ante System (Optional)

| Rule ID | Rule | Test |
|---------|------|------|
| ANTE-001 | Ante is additional forced bet from all players | Every player pays |
| ANTE-002 | Antes posted before blinds | Antes first |
| ANTE-003 | Ante typically 10-20% of big blind | Configurable amount |
| ANTE-004 | Insufficient ante: post all remaining chips | All-in ante |
| ANTE-005 | Antes go into main pot | Added to pot |

---

## 7. Player State

### 7.1 Player Properties

| Rule ID | Property | Description | Test |
|---------|----------|-------------|------|
| PLR-001 | Chip Stack | Current chip count (integer ≥ 0) | Always non-negative |
| PLR-002 | Hole Cards | 0 or 2 cards | Empty or exactly 2 |
| PLR-003 | Position | Current table position | Valid position enum |
| PLR-004 | Status | Active, folded, all-in, eliminated | Valid state enum |
| PLR-005 | Current Bet | Chips committed this round | ≥ 0 |
| PLR-006 | Total Invested | Chips committed this hand | ≥ 0 |

### 7.2 Player States

| Rule ID | State | Description | Can Act? |
|---------|-------|-------------|----------|
| STATE-001 | Active | In hand, has chips, can act | Yes |
| STATE-002 | Folded | Surrendered hand | No |
| STATE-003 | All-In | Committed all chips | No |
| STATE-004 | Eliminated | No chips, out of tournament | No |

### 7.3 State Transitions

| Rule ID | From | To | Trigger | Test |
|---------|------|-----|---------|------|
| TRANS-001 | Active | Folded | Player folds | Voluntary action |
| TRANS-002 | Active | All-In | Player bets/calls all chips | Chip count → 0 during hand |
| TRANS-003 | Active | Eliminated | Hand ends with 0 chips | Post-hand check |
| TRANS-004 | Folded | Active | New hand starts | Reset for new hand |
| TRANS-005 | All-In | Active | New hand starts (won chips) | Reset for new hand |
| TRANS-006 | All-In | Eliminated | Hand ends with 0 chips | Post-hand check |
| TRANS-007 | Eliminated | (none) | Cannot transition | Terminal state |

### 7.4 Player Reset (New Hand)

| Rule ID | Rule | Test |
|---------|------|------|
| RST-001 | Status reset to Active (if has chips) | Non-zero stack → Active |
| RST-002 | Status remains Eliminated (if no chips) | Zero stack → still Eliminated |
| RST-003 | Current Bet reset to 0 | Start fresh |
| RST-004 | Total Invested reset to 0 | Start fresh |
| RST-005 | Hole Cards cleared | No cards |

---

## 8. Action Validation

### 8.1 Fold Action

| Rule ID | Rule | Test |
|---------|------|------|
| FOLD-001 | Fold is always valid when it's player's turn | Universal action |
| FOLD-002 | Fold requires no chips | Free action |
| FOLD-003 | Fold forfeits all pot claim | Cannot win |
| FOLD-004 | Folded cards not revealed | Hidden from others |
| FOLD-005 | Player state changes to Folded | State transition |

### 8.2 Check Action

| Rule ID | Rule | Test |
|---------|------|------|
| CHECK-001 | Check valid only when no bet faces player | Current bet == player's contribution |
| CHECK-002 | Check requires no chips | Free action |
| CHECK-003 | Check passes action to next player | No pot change |
| CHECK-004 | Check invalid if there's a bet to call | Must call, raise, or fold |
| CHECK-005 | BB can check preflop if no raises | Option |

### 8.3 Call Action

| Rule ID | Rule | Test |
|---------|------|------|
| CALL-001 | Call valid when bet faces player | Current bet > player's contribution |
| CALL-002 | Call amount = current bet - player's contribution | Exact difference |
| CALL-003 | Player must have chips ≥ call amount (or all-in) | Sufficient chips |
| CALL-004 | Call matches current bet exactly | Not more, not less |
| CALL-005 | Call with insufficient chips = all-in | Partial call |

### 8.4 Bet Action

| Rule ID | Rule | Test |
|---------|------|------|
| BET-001 | Bet valid only when no current bet exists | First aggression |
| BET-002 | Minimum bet = 1 Big Blind | BB floor |
| BET-003 | Maximum bet = player's entire stack | No-limit |
| BET-004 | Bet must be whole number (chips) | Integer only |
| BET-005 | Player must have chips ≥ bet amount | Sufficient chips |
| BET-006 | Bet < BB but all-in is valid | All-in exception |

### 8.5 Raise Action

| Rule ID | Rule | Test |
|---------|------|------|
| RAISE-001 | Raise valid only when current bet exists | After bet/raise |
| RAISE-002 | Minimum raise = previous raise size (see Bet Calculation) | Min raise rule |
| RAISE-003 | Maximum raise = player's entire stack | No-limit |
| RAISE-004 | Raise must be whole number | Integer only |
| RAISE-005 | All-in for less than min raise is valid | All-in exception |
| RAISE-006 | Raise amount = (new total bet) - (player's current contribution) | Net additional chips |

### 8.6 All-In Action

| Rule ID | Rule | Test |
|---------|------|------|
| ALLIN-001 | All-in is always valid when it's player's turn | Universal action |
| ALLIN-002 | All-in commits all remaining chips | Stack → 0 |
| ALLIN-003 | All-in can be bet, call, or raise | Context dependent |
| ALLIN-004 | All-in player cannot act again this hand | State → All-In |
| ALLIN-005 | All-in player can still win pot(s) | Eligible for pots |

---

## 9. Bet Calculation

### 9.1 Minimum Bet

| Rule ID | Rule | Test |
|---------|------|------|
| MINBET-001 | Minimum opening bet = Big Blind | BB amount |
| MINBET-002 | Bet < BB invalid (unless all-in) | Rejected |
| MINBET-003 | Bet exactly = BB is valid | Minimum met |
| MINBET-004 | All-in for less than BB is valid | Exception |

### 9.2 Minimum Raise Calculation

| Rule ID | Rule | Test |
|---------|------|------|
| MINRAISE-001 | Track "last raise size" each round | Initialize to BB |
| MINRAISE-002 | Opening bet: last raise size = bet amount | First bet sets it |
| MINRAISE-003 | Subsequent raise: last raise size = (new bet - previous bet) | Delta becomes new standard |
| MINRAISE-004 | Minimum raise TO = current bet + last raise size | Formula |
| MINRAISE-005 | Minimum raise BY = last raise size | The increase portion |

### 9.3 Minimum Raise Examples

| Rule ID | Scenario | Expected | Test |
|---------|----------|----------|------|
| RAISE-EX-001 | BB=50, A bets 50 | Min raise to 100 (raise by 50) | 50 + 50 = 100 |
| RAISE-EX-002 | Current=100 (raised by 50), B raises | Min raise to 150 (raise by 50) | 100 + 50 = 150 |
| RAISE-EX-003 | Current=150 (raised by 50), C raises to 300 | C raised by 150, new min = 450 | 300 + 150 = 450 |
| RAISE-EX-004 | BB=100, A raises to 300 (raise of 200) | Min re-raise to 500 | 300 + 200 = 500 |

### 9.4 All-In Below Minimum Raise

| Rule ID | Rule | Test |
|---------|------|------|
| BELOW-001 | All-in < minimum raise = does NOT reopen betting | Original players cannot re-raise |
| BELOW-002 | All-in ≥ minimum raise = reopens betting | Full raise, action reopens |
| BELOW-003 | "Reopen" means players who already acted can raise again | Legal re-raise |
| BELOW-004 | All-in < min raise counted as call for action purposes | Not a raise |

### 9.5 All-In Reopening Examples

| Rule ID | Scenario | Reopens? | Test |
|---------|----------|----------|------|
| REOPEN-001 | Bet 200, last raise 100, all-in 230 | No (needed 300) | 30 < 100 |
| REOPEN-002 | Bet 200, last raise 100, all-in 300 | Yes (exactly min) | 100 = 100 |
| REOPEN-003 | Bet 200, last raise 100, all-in 350 | Yes (exceeds min) | 150 > 100 |

---

## 10. Pot Management

### 10.1 Pot Structure

| Rule ID | Rule | Test |
|---------|------|------|
| POT-001 | Pot starts at 0 each hand | Initialize empty |
| POT-002 | All bets/calls/raises add to pot | Accumulate |
| POT-003 | Pot never decreases during hand (except uncalled bets) | Monotonic increase |
| POT-004 | Pot is sum of all player contributions | Total wagered |
| POT-005 | Track each player's total investment | Per-player accounting |

### 10.2 Contribution Tracking

| Rule ID | Rule | Test |
|---------|------|------|
| CONTRIB-001 | Track chips contributed per player per round | Round-level tracking |
| CONTRIB-002 | Track total chips contributed per player per hand | Hand-level tracking |
| CONTRIB-003 | Reset round contribution at start of each betting round | Flop/turn/river reset |
| CONTRIB-004 | Maintain hand contribution until hand ends | Cumulative |

### 10.3 Uncalled Bet Return

| Rule ID | Rule | Test |
|---------|------|------|
| UNCALL-001 | If bet/raise not called by anyone, return excess | Overage returned |
| UNCALL-002 | Uncalled amount = bet amount - highest call | Difference |
| UNCALL-003 | Return occurs before pot award | Clean up first |
| UNCALL-004 | All-in less than bet: return difference to bettor | Immediate return |

### 10.4 Uncalled Bet Examples

| Rule ID | Scenario | Returned | Test |
|---------|----------|----------|------|
| UNCALL-EX-001 | A bets 500, all fold | 500 returned to A (wins blinds only) | No callers |
| UNCALL-EX-002 | A bets 500, B all-in 200, C folds | 300 returned to A | B can only match 200 |
| UNCALL-EX-003 | A bets 500, B calls 500 | 0 returned | Full call |

---

## 11. Side Pot System

### 11.1 When Side Pots Are Created

| Rule ID | Rule | Test |
|---------|------|------|
| SIDE-001 | Side pot created when all-in player can't match full bet | Insufficient chips |
| SIDE-002 | Multiple side pots possible | Multiple all-in levels |
| SIDE-003 | Main pot = smallest common contribution × players | Everyone eligible |
| SIDE-004 | Side pot = excess contributions | Limited eligibility |

### 11.2 Side Pot Calculation Algorithm

| Rule ID | Step | Description | Test |
|---------|------|-------------|------|
| CALC-001 | 1 | List all players with total contributions | Get totals |
| CALC-002 | 2 | Sort by contribution ascending | Lowest first |
| CALC-003 | 3 | For each level, create pot | Iterate levels |
| CALC-004 | 4 | Pot amount = (level - prev level) × eligible players | Calculate |
| CALC-005 | 5 | Track eligibility for each pot | Who can win |

### 11.3 Side Pot Example

| Rule ID | Scenario | Calculation | Test |
|---------|----------|-------------|------|
| SIDE-EX-001 | A: 100, B: 300, C: 500, D: 500 | Main: 100×4=400 | A,B,C,D eligible |
| SIDE-EX-002 | (continued) | Side 1: 200×3=600 | B,C,D eligible |
| SIDE-EX-003 | (continued) | Side 2: 200×2=400 | C,D eligible |
| SIDE-EX-004 | (continued) | Total: 1400 | Sum of all pots |

### 11.4 Side Pot Eligibility

| Rule ID | Rule | Test |
|---------|------|------|
| ELIG-001 | Player eligible for pot if contributed to it | Must have chips in pot |
| ELIG-002 | Folded players not eligible for any pot | Fold = forfeit |
| ELIG-003 | All-in players eligible for pots up to their level | Limited by contribution |
| ELIG-004 | Active players eligible for all pots they contributed to | Full eligibility |

### 11.5 Side Pot Award Order

| Rule ID | Rule | Test |
|---------|------|------|
| AWARD-001 | Award highest side pot first (fewest eligible) | Top pot first |
| AWARD-002 | Proceed to lower pots | Work down |
| AWARD-003 | Award main pot last | Most eligible |
| AWARD-004 | Best hand among eligible wins each pot | Compare eligible only |
| AWARD-005 | Folded players cannot win any pot | Already forfeited |

---

## 12. Betting Round

### 12.1 Betting Round Initialization

| Rule ID | Rule | Test |
|---------|------|------|
| RDINIT-001 | Current bet = 0 at start of postflop rounds | Fresh round |
| RDINIT-002 | Current bet = BB at start of preflop | Blinds count |
| RDINIT-003 | Last raise size = BB at start | Initialize |
| RDINIT-004 | All round contributions reset to 0 (except blinds preflop) | Clean slate |
| RDINIT-005 | Determine first actor per position rules | Start action |

### 12.2 Action Processing

| Rule ID | Rule | Test |
|---------|------|------|
| PROC-001 | Validate action is legal | Check rules |
| PROC-002 | Update player's chip stack | Deduct/add |
| PROC-003 | Update player's round contribution | Track bet |
| PROC-004 | Update player's hand contribution | Track total |
| PROC-005 | Update pot | Add chips |
| PROC-006 | Update current bet (if bet/raise) | New target |
| PROC-007 | Update last raise size (if raise) | New minimum |
| PROC-008 | Update player state (if fold/all-in) | State change |
| PROC-009 | Advance to next actor | Next player |

### 12.3 Betting Round Completion

| Rule ID | Rule | Test |
|---------|------|------|
| COMP-001 | Round ends when all but one folded | Early end |
| COMP-002 | Round ends when all active players matched bet and acted | Full round |
| COMP-003 | All-in players don't need to act | Skip in rotation |
| COMP-004 | Folded players don't need to act | Skip in rotation |
| COMP-005 | BB option: if no raise preflop, BB gets final option | Special case |

### 12.4 BB Option

| Rule ID | Rule | Test |
|---------|------|------|
| BBOPT-001 | If no raises preflop, BB can check or raise | Final option |
| BBOPT-002 | If BB checks, preflop ends | Round complete |
| BBOPT-003 | If BB raises, action continues | Reopen |
| BBOPT-004 | BB option only applies preflop | Not postflop |

### 12.5 Round Completion Detection

| Rule ID | Condition | Round Complete? | Test |
|---------|-----------|-----------------|------|
| DETECT-001 | All but one folded | Yes (hand ends) | Immediate |
| DETECT-002 | All players all-in | Yes | No one can act |
| DETECT-003 | All players checked | Yes | No bet made |
| DETECT-004 | All active players called highest bet | Yes | Bets matched |
| DETECT-005 | BB hasn't acted preflop (no raise) | No | BB option pending |

---

## 13. Deal Progression

### 13.1 Pre-Deal

| Rule ID | Step | Description | Test |
|---------|------|-------------|------|
| PREDEAL-001 | 1 | Create and shuffle new deck | 52 cards |
| PREDEAL-002 | 2 | Determine button position | Assign dealer |
| PREDEAL-003 | 3 | Post small blind | SB deducted |
| PREDEAL-004 | 4 | Post big blind | BB deducted |
| PREDEAL-005 | 5 | Post antes (if applicable) | All pay |

### 13.2 Hole Card Deal

| Rule ID | Step | Description | Test |
|---------|------|-------------|------|
| HOLE-001 | 1 | Start with player left of button (SB) | First card |
| HOLE-002 | 2 | Deal one card face-down to each player | Clockwise |
| HOLE-003 | 3 | Repeat for second card | Same order |
| HOLE-004 | 4 | Each player has exactly 2 cards | Verify count |
| HOLE-005 | 5 | Cards are private (hidden from others) | Not visible |

### 13.3 Flop Deal

| Rule ID | Step | Description | Test |
|---------|------|-------------|------|
| FLOP-001 | 1 | Burn one card | Top card discarded |
| FLOP-002 | 2 | Deal three cards face-up | Community cards |
| FLOP-003 | 3 | Three community cards visible | Board = 3 cards |
| FLOP-004 | Prerequisite | Preflop betting complete | Must finish preflop |

### 13.4 Turn Deal

| Rule ID | Step | Description | Test |
|---------|------|-------------|------|
| TURN-001 | 1 | Burn one card | Top card discarded |
| TURN-002 | 2 | Deal one card face-up | Fourth community card |
| TURN-003 | 3 | Four community cards visible | Board = 4 cards |
| TURN-004 | Prerequisite | Flop betting complete | Must finish flop |

### 13.5 River Deal

| Rule ID | Step | Description | Test |
|---------|------|-------------|------|
| RIVER-001 | 1 | Burn one card | Top card discarded |
| RIVER-002 | 2 | Deal one card face-up | Fifth community card |
| RIVER-003 | 3 | Five community cards visible | Board = 5 cards |
| RIVER-004 | Prerequisite | Turn betting complete | Must finish turn |

### 13.6 Card Counts by Stage

| Rule ID | Stage | Deck Remaining | Community | Total Dealt | Test |
|---------|-------|----------------|-----------|-------------|------|
| COUNT-001 | Start | 52 | 0 | 0 | Fresh deck |
| COUNT-002 | After hole cards (4p) | 44 | 0 | 8 | 4×2 players |
| COUNT-003 | After hole cards (6p) | 40 | 0 | 12 | 6×2 players |
| COUNT-004 | After flop | 40-4=36 (4p) | 3 | 12 | Burn+3 |
| COUNT-005 | After turn | 36-2=34 (4p) | 4 | 14 | Burn+1 |
| COUNT-006 | After river | 34-2=32 (4p) | 5 | 16 | Burn+1 |

---

## 14. Showdown

### 14.1 Showdown Trigger

| Rule ID | Rule | Test |
|---------|------|------|
| SHOW-001 | Showdown occurs after river betting if 2+ players remain | Final betting done |
| SHOW-002 | No showdown if all but one fold | Winner by default |
| SHOW-003 | Showdown can occur earlier if all remaining players all-in | Run out board |

### 14.2 Showdown Order

| Rule ID | Rule | Test |
|---------|------|------|
| ORDER-001 | If river bet/raise: last aggressor shows first | Aggressor first |
| ORDER-002 | If river checked: first player left of button shows first | Position order |
| ORDER-003 | Remaining players show clockwise | Sequential |
| ORDER-004 | In software: all players show simultaneously | Simplified |

### 14.3 Hand Revelation

| Rule ID | Rule | Test |
|---------|------|------|
| REVEAL-001 | All showdown players must reveal hole cards | Mandatory |
| REVEAL-002 | Both hole cards revealed | Show both |
| REVEAL-003 | Community cards combined with hole cards | 7 total cards |
| REVEAL-004 | Best 5-card hand evaluated | Hand ranking applied |

### 14.4 Winner Determination

| Rule ID | Rule | Test |
|---------|------|------|
| WIN-001 | Best 5-card hand wins | Highest ranking |
| WIN-002 | Compare all showdown players | Full comparison |
| WIN-003 | Tiebreaker rules apply for same rank | See Hand Comparison |
| WIN-004 | Multiple winners possible (tie) | Split pot |

### 14.5 Pot Award at Showdown

| Rule ID | Rule | Test |
|---------|------|------|
| AWARD-SHOW-001 | If single winner: winner takes entire pot | Simple case |
| AWARD-SHOW-002 | If tie: split pot equally | Divide evenly |
| AWARD-SHOW-003 | If odd chip: first player left of button gets it | Odd chip rule |
| AWARD-SHOW-004 | If side pots: award each separately | Per-pot winners |
| AWARD-SHOW-005 | Side pot winners only from eligible players | Eligibility check |

---

## 15. Hand Lifecycle

### 15.1 Hand States

| Rule ID | State | Description | Test |
|---------|-------|-------------|------|
| HSTATE-001 | SETUP | Pre-deal, posting blinds | Initial |
| HSTATE-002 | PREFLOP | Hole cards dealt, first betting | Stage 1 |
| HSTATE-003 | FLOP | Three community cards, second betting | Stage 2 |
| HSTATE-004 | TURN | Fourth community card, third betting | Stage 3 |
| HSTATE-005 | RIVER | Fifth community card, final betting | Stage 4 |
| HSTATE-006 | SHOWDOWN | Comparing hands, awarding pot | Resolution |
| HSTATE-007 | COMPLETE | Hand finished | Terminal |

### 15.2 Hand State Transitions

| Rule ID | From | To | Condition | Test |
|---------|------|-----|-----------|------|
| HTRANS-001 | SETUP | PREFLOP | Blinds posted, cards dealt | Automatic |
| HTRANS-002 | PREFLOP | FLOP | Preflop betting complete, 2+ players | Continue |
| HTRANS-003 | PREFLOP | COMPLETE | All but one fold | Early end |
| HTRANS-004 | FLOP | TURN | Flop betting complete, 2+ players | Continue |
| HTRANS-005 | FLOP | COMPLETE | All but one fold | Early end |
| HTRANS-006 | TURN | RIVER | Turn betting complete, 2+ players | Continue |
| HTRANS-007 | TURN | COMPLETE | All but one fold | Early end |
| HTRANS-008 | RIVER | SHOWDOWN | River betting complete, 2+ players | Showdown |
| HTRANS-009 | RIVER | COMPLETE | All but one fold | Early end |
| HTRANS-010 | SHOWDOWN | COMPLETE | Pot awarded | Automatic |

### 15.3 Early Hand Termination

| Rule ID | Rule | Test |
|---------|------|------|
| EARLY-001 | Hand ends immediately if all but one fold | No continuation |
| EARLY-002 | Remaining player wins pot without showdown | Default win |
| EARLY-003 | No cards revealed | Privacy preserved |
| EARLY-004 | Skip remaining betting rounds and showdown | Jump to complete |

### 15.4 All-In Run Out

| Rule ID | Rule | Test |
|---------|------|------|
| RUNOUT-001 | If all active players all-in, deal remaining cards | No more betting |
| RUNOUT-002 | Run out flop if preflop all-in | Deal all 5 |
| RUNOUT-003 | Run out turn+river if flop all-in | Deal remaining |
| RUNOUT-004 | Run out river if turn all-in | Deal last card |
| RUNOUT-005 | Proceed directly to showdown | Skip betting |

### 15.5 Hand Cleanup

| Rule ID | Rule | Test |
|---------|------|------|
| CLEAN-001 | Award pot(s) to winner(s) | Distribute chips |
| CLEAN-002 | Return uncalled bets | Refund excess |
| CLEAN-003 | Check for eliminated players | 0 chips |
| CLEAN-004 | Update tournament standings | Position changes |
| CLEAN-005 | Move button | Rotate dealer |
| CLEAN-006 | Increment hand counter | Track progress |
| CLEAN-007 | Check for blind level increase | Per schedule |

---

## 16. Player Elimination

### 16.1 Elimination Conditions

| Rule ID | Rule | Test |
|---------|------|------|
| ELIM-001 | Player eliminated when chip count = 0 after hand | Post-hand check |
| ELIM-002 | Elimination only processed after hand completes | Not mid-hand |
| ELIM-003 | Player can't be eliminated if they win all-in | May recover |

### 16.2 Elimination Processing

| Rule ID | Rule | Test |
|---------|------|------|
| ELIMPROC-001 | Mark player as eliminated | State change |
| ELIMPROC-002 | Assign finish position | Based on order |
| ELIMPROC-003 | Remove from active player list | No longer plays |
| ELIMPROC-004 | Record elimination time/hand | For tiebreaking |

### 16.3 Simultaneous Elimination

| Rule ID | Rule | Test |
|---------|------|------|
| SIMUL-001 | Multiple players can bust same hand | All-in scenarios |
| SIMUL-002 | Higher starting stack = better finish position | Tiebreaker |
| SIMUL-003 | Same starting stack = tied position | Share position |
| SIMUL-004 | Compare stack at hand START, not all-in moment | Timing matters |

### 16.4 Simultaneous Elimination Example

| Rule ID | Scenario | Finish Position | Test |
|---------|----------|-----------------|------|
| SIMUL-EX-001 | 4 players remain, A(500) and B(300) bust | B=4th, A=3rd | B had fewer |
| SIMUL-EX-002 | A(400) and B(400) bust same hand | A=3rd, B=3rd (tie) | Equal stacks |

### 16.5 Post-Elimination Adjustments

| Rule ID | Rule | Test |
|---------|------|------|
| POSTADJ-001 | Button skips eliminated seats | Active players only |
| POSTADJ-002 | Blinds skip eliminated seats | Active players only |
| POSTADJ-003 | Transition to heads-up rules if 2 remain | Special rules apply |
| POSTADJ-004 | Check for tournament end if 1 remains | Winner determined |

---

## 17. Tournament Progression

### 17.1 Tournament States

| Rule ID | State | Description | Test |
|---------|-------|-------------|------|
| TSTATE-001 | WAITING | Waiting for players to join | Pre-start |
| TSTATE-002 | STARTING | Game about to begin | Transition |
| TSTATE-003 | ACTIVE | Game in progress | Running |
| TSTATE-004 | PAUSED | Game temporarily halted | System pause |
| TSTATE-005 | COMPLETE | Winner determined | Terminal |
| TSTATE-006 | CANCELLED | Game cancelled (didn't fill) | Terminal |

### 17.2 Tournament Initialization

| Rule ID | Rule | Test |
|---------|------|------|
| TINIT-001 | All players start with equal chip counts | Fair start |
| TINIT-002 | Starting chips defined by tournament config | Configurable |
| TINIT-003 | Button assigned randomly | No advantage |
| TINIT-004 | Blind level starts at level 1 | First level |

### 17.3 Between-Hand Processing

| Rule ID | Step | Description | Test |
|---------|------|-------------|------|
| BETWEEN-001 | 1 | Process eliminations | Remove 0-chip players |
| BETWEEN-002 | 2 | Check tournament end | 1 player = winner |
| BETWEEN-003 | 3 | Rotate button | Move clockwise |
| BETWEEN-004 | 4 | Check blind increase | Per schedule |
| BETWEEN-005 | 5 | Apply new blinds if needed | Level up |
| BETWEEN-006 | 6 | Reset player states for new hand | Fresh hand |

### 17.4 Blind Level Management

| Rule ID | Rule | Test |
|---------|------|------|
| BLINDMGMT-001 | Track current blind level | Level number |
| BLINDMGMT-002 | Track hands/time at current level | Progress |
| BLINDMGMT-003 | Increase level when threshold reached | Trigger |
| BLINDMGMT-004 | Apply new SB/BB from schedule | Update amounts |
| BLINDMGMT-005 | Notify players of blind increase | Communication |

### 17.5 Tournament End Conditions

| Rule ID | Rule | Test |
|---------|------|------|
| TEND-001 | Tournament ends when 1 player has all chips | Winner |
| TEND-002 | Final player is rank 1 (winner) | First place |
| TEND-003 | Calculate final standings | All positions |
| TEND-004 | Distribute prizes per payout structure | Payouts |

### 17.6 Finish Position Assignment

| Rule ID | Rule | Test |
|---------|------|------|
| FINISH-001 | First eliminated = last place | Worst position |
| FINISH-002 | Last remaining = first place | Winner |
| FINISH-003 | Positions assigned in elimination order | Sequential |
| FINISH-004 | Simultaneous elimination: stack size tiebreaker | More chips = better |

---

## 18. Timeout Handling

### 18.1 Turn Time Limits

| Rule ID | Rule | Test |
|---------|------|------|
| TIME-001 | Each turn has maximum time limit | Configurable |
| TIME-002 | Timer starts when action is on player | Turn begins |
| TIME-003 | Timer stops when valid action submitted | Turn ends |
| TIME-004 | Suggested limit: 30-60 seconds | Default range |

### 18.2 Timeout Actions

| Rule ID | Rule | Test |
|---------|------|------|
| TIMEOUT-001 | First timeout: Warning issued | Notify player |
| TIMEOUT-002 | First timeout action: Auto-check if possible | Preserve equity |
| TIMEOUT-003 | First timeout action: Auto-fold if check not possible | Default action |
| TIMEOUT-004 | Repeated timeout: Auto-fold | Stricter penalty |

### 18.3 Timeout Logic

| Rule ID | Condition | Action | Test |
|---------|-----------|--------|------|
| TLOGIC-001 | Timeout + no bet facing | Auto-check | Free check |
| TLOGIC-002 | Timeout + bet facing + first offense | Auto-fold + warning | One chance |
| TLOGIC-003 | Timeout + bet facing + repeat offense | Auto-fold | No leniency |
| TLOGIC-004 | Timeout + all-in situation | Auto-fold | Must act |

### 18.4 Timeout Tracking

| Rule ID | Rule | Test |
|---------|------|------|
| TRACK-001 | Track timeout count per player per tournament | Persistent |
| TRACK-002 | Reset timeout count at tournament start | Fresh start |
| TRACK-003 | Do NOT reset between hands | Cumulative |
| TRACK-004 | Log all timeouts for audit | Traceability |

---

## Appendix A: Summary Rule Counts

| Component | Rule Count |
|-----------|------------|
| Card System | 13 |
| Deck System | 13 |
| Hand Evaluation | 32 |
| Hand Comparison | 13 |
| Position System | 22 |
| Blind System | 19 |
| Player State | 18 |
| Action Validation | 25 |
| Bet Calculation | 18 |
| Pot Management | 12 |
| Side Pot System | 17 |
| Betting Round | 20 |
| Deal Progression | 24 |
| Showdown | 15 |
| Hand Lifecycle | 21 |
| Player Elimination | 14 |
| Tournament Progression | 21 |
| Timeout Handling | 14 |
| **TOTAL** | **311** |

---

## Appendix B: Dependency Matrix

| Component | Depends On |
|-----------|------------|
| Card System | (none) |
| Deck System | Card System |
| Hand Evaluation | Card System |
| Hand Comparison | Hand Evaluation |
| Position System | Player State |
| Blind System | Pot Management, Position System |
| Player State | Pot Management |
| Action Validation | Bet Calculation |
| Bet Calculation | Blind System |
| Pot Management | (none) |
| Side Pot System | Pot Management |
| Betting Round | Action Validation, Position System, Pot Management |
| Deal Progression | Deck System, Betting Round |
| Showdown | Hand Comparison, Side Pot System |
| Hand Lifecycle | Deal Progression, Betting Round, Showdown |
| Player Elimination | Player State, Pot Management |
| Tournament Progression | Hand Lifecycle, Player Elimination, Blind System |
| Timeout Handling | Betting Round |

---

## Appendix C: Test Priority Matrix

| Priority | Components | Reason |
|----------|------------|--------|
| P0 (Critical) | Hand Evaluation, Hand Comparison | Core correctness |
| P0 (Critical) | Pot Management, Side Pot System | Money handling |
| P0 (Critical) | Action Validation, Bet Calculation | Legal move enforcement |
| P1 (High) | Betting Round, Deal Progression | Game flow |
| P1 (High) | Player State, Player Elimination | State management |
| P2 (Medium) | Position System, Blind System | Order and structure |
| P2 (Medium) | Tournament Progression | Game lifecycle |
| P3 (Low) | Card System, Deck System | Foundation (simple) |
| P3 (Low) | Timeout Handling | Edge case handling |

---

## Appendix D: Edge Case Index

| ID | Component | Edge Case | Rule Reference |
|----|-----------|-----------|----------------|
| EC-001 | Hand Evaluation | Wheel straight (A-2-3-4-5) | STR-002 |
| EC-002 | Hand Evaluation | Broadway (10-J-Q-K-A) | STR-003 |
| EC-003 | Hand Evaluation | Invalid wrap (K-A-2-3-4) | STR-004 |
| EC-004 | Hand Evaluation | Play the board | BEST-006 |
| EC-005 | Position System | Heads-up button is SB | HU-001 |
| EC-006 | Position System | Heads-up action order flip | HU-003, HU-004 |
| EC-007 | Blind System | All-in for partial blind | SHORT-001 |
| EC-008 | Bet Calculation | All-in below minimum raise | BELOW-001 |
| EC-009 | Bet Calculation | All-in reopens action | BELOW-002 |
| EC-010 | Pot Management | Uncalled bet return | UNCALL-001 |
| EC-011 | Side Pot System | Multiple all-in levels | SIDE-001 |
| EC-012 | Betting Round | BB option preflop | BBOPT-001 |
| EC-013 | Hand Lifecycle | All players all-in run out | RUNOUT-001 |
| EC-014 | Elimination | Simultaneous elimination | SIMUL-001 |
| EC-015 | Showdown | Tie with odd chip | AWARD-SHOW-003 |
| EC-016 | Showdown | Board plays (all tie) | BOARD-001 |

---

*End of Atomic Rules Specification*