"""Format game record for LLM context."""

from __future__ import annotations

from src.application.poker.records.models import GameRecord, HandRecord
from src.domain.rules.hand_evaluator import HandEvaluation, HandRank


class RecordFormatter:
    """Formats game record into concise text for LLM context.

    Produces a dense, parseable format optimized for LLM comprehension.
    """

    @staticmethod
    def format_hand_actions(hand: HandRecord) -> dict[str, list[str]]:
        """Format all actions in a hand grouped by phase.

        Args:
            hand: The hand record to format.

        Returns:
            Dictionary mapping phase names to lists of action strings.
        """
        phase_actions: dict[str, list[str]] = {}

        # Iterate through rounds (new hierarchical structure)
        for round_record in hand.rounds:
            phase_name = round_record.phase.value.upper()
            if phase_name not in phase_actions:
                phase_actions[phase_name] = []

            # Iterate through turns in this round
            for turn in round_record.turns:
                action = turn.action
                action_str = action.to_short_string()

                # Get position for this player
                player_record = hand.player_records.get(action.player_id)
                if player_record and player_record.position:
                    position_str = player_record.position.value.upper()
                    player_label = f"{action.player_name}({position_str})"
                else:
                    # Fallback if position not available
                    player_label = action.player_name

                phase_actions[phase_name].append(f"{player_label}:{action_str}")

        return phase_actions

    @staticmethod
    def format_hand_summary(hand: HandRecord, viewer_id: str | None = None) -> str:
        """Format a completed hand as a one-line summary.

        Args:
            hand: The completed hand to summarize.
            viewer_id: Optional viewer's player_id to personalize ("you").

        Returns:
            One-line summary string.

        Example:
            "H4: Winner=BB, Pot=200, Showdown=no"
            "H3: Winner=UTG, Pot=850, Showdown=yes, UTG showed QQ"
        """
        if hand.outcome is None:
            return f"H{hand.hand_number}: (incomplete)"

        outcome = hand.outcome
        winner_names = []
        for winner_id in outcome.winner_ids:
            # Check if this is the viewer
            if viewer_id and winner_id == viewer_id:
                winner_names.append("you")
            else:
                # Try to find name from showdown results or player outcomes
                name = winner_id
                for po in outcome.player_outcomes:
                    if po.player_id == winner_id:
                        name = po.player_name
                        break
                winner_names.append(name)

        winners_str = ",".join(winner_names)
        showdown_str = "yes" if outcome.was_showdown else "no"

        summary = f"H{hand.hand_number}: Winner={winners_str}, Pot={outcome.pot_amount.value}, Showdown={showdown_str}"

        # Add showdown details if applicable
        if outcome.was_showdown and outcome.showdown_results:
            shown_hands = []
            for sr in outcome.showdown_results:
                name = "you" if viewer_id and sr.player_id == viewer_id else sr.player_name
                hole_cards_str = str(sr.hole_cards)
                shown_hands.append(f"{name} showed {hole_cards_str}")
            summary += f", {'; '.join(shown_hands)}"

        return summary

    @staticmethod
    def format_hand_starting_stacks(hand: HandRecord, viewer_id: str | None = None) -> str:
        """Format starting stack sizes for a hand.

        Args:
            hand: The hand to format stacks for.
            viewer_id: Optional viewer's player_id to personalize ("you").

        Returns:
            Formatted stack string.

        Example:
            "  Stacks: Alice(BUTTON)=1000, Bob(SB)=950, Carol(BB)=1200"
        """
        stack_strs = []
        for player_id, player_record in hand.player_records.items():
            name = "you" if viewer_id and player_id == viewer_id else player_record.player_name
            position_str = ""
            if player_record.position:
                # Abbreviate position names for compactness
                pos_abbrev = {
                    "button": "BTN",
                    "small_blind": "SB",
                    "big_blind": "BB",
                    "BUTTON": "BTN",
                    "SMALL_BLIND": "SB",
                    "BIG_BLIND": "BB",
                }.get(player_record.position.value, player_record.position.value[:3].upper())
                position_str = f"({pos_abbrev})"
            stack_strs.append(f"{name}{position_str}={player_record.starting_chips.value}")

        return f"  Stacks: {', '.join(stack_strs)}"

    @staticmethod
    def format_recent_records(
        record: GameRecord,
        viewer_id: str | None = None,
        max_hands: int = 5,
    ) -> str:
        """Format recent game record for LLM context.

        Args:
            record: The game record to format.
            viewer_id: Optional viewer's player_id to personalize output.
            max_hands: Maximum number of recent hands to include.

        Returns:
            Formatted record string.

        Example output:
            === PREVIOUS HANDS ===
            H4: Winner=BB, Pot=200, Showdown=no
              Stacks: Alice(BTN)=1000, Bob(SB)=950, Carol(BB)=1200
              PRE_FLOP: Alice(BUTTON):R100, Bob(SMALL_BLIND):F, Carol(BIG_BLIND):C
              FLOP: Carol(BIG_BLIND):X, Alice(BUTTON):B150, Carol(BIG_BLIND):F
            H3: Winner=Dave, Pot=850, Showdown=yes, Dave showed Q♥Q♦
              Stacks: Dave=1100, Alice(BTN)=1050, Bob(SB)=940, Carol(BB)=1210
              PRE_FLOP: Dave:R200, Alice(BUTTON):C, Bob(SMALL_BLIND):F, Carol(BIG_BLIND):C
              FLOP: Carol(BIG_BLIND):X, Dave:B300, Alice(BUTTON):F, Carol(BIG_BLIND):C
              TURN: Carol(BIG_BLIND):X, Dave:AI350, Carol(BIG_BLIND):C
        """
        recent = record.get_recent_hands(max_hands)

        if not recent:
            return ""

        lines = ["=== PREVIOUS HANDS ==="]
        for hand in recent:
            # Add summary line
            lines.append(RecordFormatter.format_hand_summary(hand, viewer_id))

            # Add starting stacks
            lines.append(RecordFormatter.format_hand_starting_stacks(hand, viewer_id))

            # Add actions for this hand
            if hand.rounds:
                phase_actions = RecordFormatter.format_hand_actions(hand)
                phase_order = ["PRE_FLOP", "FLOP", "TURN", "RIVER"]

                for phase in phase_order:
                    if phase in phase_actions:
                        actions_str = ", ".join(phase_actions[phase])
                        lines.append(f"  {phase}: {actions_str}")

        return "\n".join(lines)

    @staticmethod
    def format_hand_description(evaluation: HandEvaluation) -> str:
        """Format a HandEvaluation to a human-readable description.

        Examples:
            "Royal Flush"
            "Straight Flush, King-high"
            "Four of a Kind, Aces"
            "Full House, Kings over Sevens"
            "Flush, Ace-high"
            "Straight, Ten-high"
            "Three of a Kind, Eights"
            "Two Pair, Aces and Kings"
            "Pair of Jacks"
            "High Card, Ace"

        Args:
            evaluation: The hand evaluation to format.

        Returns:
            Human-readable hand description.
        """
        rank_name = str(evaluation.rank)

        # For hands that need rank details, add them
        if evaluation.rank == HandRank.ROYAL_FLUSH:
            return rank_name

        if evaluation.rank == HandRank.STRAIGHT_FLUSH:
            high_rank = evaluation.kickers[0]
            return f"{rank_name}, {high_rank.to_short_string()}-high"

        if evaluation.rank == HandRank.FOUR_OF_A_KIND:
            quad_rank = evaluation.kickers[0]
            return f"Four of a Kind, {quad_rank.to_long_string()}s"

        if evaluation.rank == HandRank.FULL_HOUSE:
            trips_rank = evaluation.kickers[0]
            pair_rank = evaluation.kickers[1]
            return f"{rank_name}, {trips_rank.to_long_string()}s over {pair_rank.to_long_string()}s"

        if evaluation.rank == HandRank.FLUSH:
            high_rank = evaluation.kickers[0]
            return f"{rank_name}, {high_rank.to_short_string()}-high"

        if evaluation.rank == HandRank.STRAIGHT:
            high_rank = evaluation.kickers[0]
            return f"{rank_name}, {high_rank.to_short_string()}-high"

        if evaluation.rank == HandRank.THREE_OF_A_KIND:
            trips_rank = evaluation.kickers[0]
            return f"{rank_name}, {trips_rank.to_long_string()}s"

        if evaluation.rank == HandRank.TWO_PAIR:
            high_pair = evaluation.kickers[0]
            low_pair = evaluation.kickers[1]
            return f"{rank_name}, {high_pair.to_long_string()}s and {low_pair.to_long_string()}s"

        if evaluation.rank == HandRank.PAIR:
            pair_rank = evaluation.kickers[0]
            return f"Pair of {pair_rank.to_long_string()}s"

        # HIGH_CARD
        high_rank = evaluation.kickers[0]
        return f"{rank_name}, {high_rank.to_short_string()}"

    @staticmethod
    def format_current_hand_actions(
        hand: HandRecord,
        current_phase: str,
    ) -> str:
        """Format actions from the current hand for LLM context.

        Args:
            hand: The current hand record.
            current_phase: The current phase name (for highlighting).

        Returns:
            Formatted actions string.

        Example output:
            ACTIONS THIS HAND:
              PRE_FLOP: Alice(BUTTON):R100, Bob(SMALL_BLIND):C, Carol(BIG_BLIND):C
              FLOP: Alice(BUTTON):R150, Carol(BIG_BLIND):C, Bob(SMALL_BLIND):F, ?
        """
        # Check if there are any rounds with turns
        if not hand.rounds:
            return ""

        phase_actions = RecordFormatter.format_hand_actions(hand)

        lines = ["ACTIONS THIS HAND:"]
        phase_order = ["PRE_FLOP", "FLOP", "TURN", "RIVER"]

        for phase in phase_order:
            if phase in phase_actions:
                actions_str = ", ".join(phase_actions[phase])
                # Mark current phase with ? to indicate pending action
                if phase == current_phase.upper():
                    actions_str += ", ?"
                lines.append(f"  {phase}: {actions_str}")
            elif phase == current_phase.upper():
                # Current phase with no actions yet
                lines.append(f"  {phase}: ?")

        return "\n".join(lines)
