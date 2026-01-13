from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

NarrationText = NewType("NarrationText", str)


@dataclass(frozen=True, slots=True)
class Narration:
    game_stage_assessment: NarrationText
    positional_context: NarrationText
    range_analysis: NarrationText
    equity_assessment: NarrationText
    opponent_modeling: NarrationText
    bet_sizing_rationale: NarrationText
    multi_street_plan: NarrationText
    meta_considerations: NarrationText
    final_decision: NarrationText

    def __post_init__(self) -> None:
        if not self.game_stage_assessment.strip():
            raise ValueError("game_stage_assessment cannot be empty")
        if not self.positional_context.strip():
            raise ValueError("positional_context cannot be empty")
        if not self.range_analysis.strip():
            raise ValueError("range_analysis cannot be empty")
        if not self.equity_assessment.strip():
            raise ValueError("equity_assessment cannot be empty")
        if not self.opponent_modeling.strip():
            raise ValueError("opponent_modeling cannot be empty")
        if not self.bet_sizing_rationale.strip():
            raise ValueError("bet_sizing_rationale cannot be empty")
        if not self.multi_street_plan.strip():
            raise ValueError("multi_street_plan cannot be empty")
        if not self.meta_considerations.strip():
            raise ValueError("meta_considerations cannot be empty")
        if not self.final_decision.strip():
            raise ValueError("final_decision cannot be empty")


# Narration Field Specifications
#
# Each field should be concise but insightful, written from the perspective of an elite
# poker player (e.g., Daniel Negreanu, Phil Ivey). Maximum lengths are guidelines to
# maintain readability and pacing - quality over verbosity.
#
# game_stage_assessment (max ~80 words)
#   Assess the current stage of the tournament/game and how it affects strategy.
#   Include: tournament phase (early/mid/late/bubble/final table), blind level relative
#   to stack sizes, number of players remaining, payout structure implications, survival
#   vs. accumulation priorities. Explain how stage context shapes risk tolerance and
#   decision-making approach.
#
# positional_context (max ~60 words)
#   Analyze position at the table, stack sizes, pot odds, and effective stack depth.
#   Include: seat position (early/middle/late/blinds), stack size in big blinds,
#   pot size and pot odds, effective stack with opponents, number of players in the hand,
#   action that has occurred. Set the tactical context for the decision.
#
# range_analysis (max ~100 words)
#   Construct opponent ranges based on their actions, position, and history.
#   Include: what hands opponents can have given their actions, how position affects
#   their range, how betting patterns narrow ranges, what hands are eliminated or
#   likely based on action. Think in terms of hand combinations, not just "they might
#   have a good hand." Be specific about range construction and narrowing.
#
# equity_assessment (max ~80 words)
#   Evaluate hand strength and equity against opponent ranges, including implied odds.
#   Include: current hand strength vs. constructed opponent ranges, pot equity percentage,
#   implied odds if drawing, fold equity if betting, how equity changes on different
#   board textures. Be mathematically precise but explain in accessible terms. Consider
#   both made hands and drawing hands.
#
# opponent_modeling (max ~70 words)
#   Model opponent tendencies, patterns, and exploitable weaknesses.
#   Include: observed betting patterns, recent hand history, tight/loose tendencies,
#   aggressive/passive style, specific exploitable behaviors (e.g., "folds to 3-bets
#   frequently," "calls too wide in position"). Explain how this decision affects their
#   perception of you and how you can exploit their tendencies.
#
# bet_sizing_rationale (max ~60 words)
#   Explain why this specific bet size was chosen, not just the action type.
#   Include: value extraction sizing, bluff sizing relative to pot, pot control sizing,
#   protection sizing, inducing sizing. Explain how the size tells the story you want
#   and achieves your goal (value, bluff, protection, etc.). Be specific about why this
#   size rather than larger or smaller.
#
# multi_street_plan (max ~80 words)
#   Plan for future streets (turn/river) based on this decision and potential outcomes.
#   Include: continuation betting strategy, checking back plans, bluffing lines, value
#   betting lines, how different board textures affect the plan. Explain how this current
#   decision sets up future streets and what you'll do in various scenarios. Think ahead
#   multiple streets, not just the current action.
#
# meta_considerations (max ~70 words)
#   Consider table image, stack dynamics, tournament implications, and meta-game factors.
#   Include: how this decision affects your table image, stack dynamics and chip
#   distribution, ICM implications in tournaments, how this affects future hands,
#   balance vs. exploitation considerations. Explain the broader strategic implications
#   beyond just this one hand.
#
# final_decision (max ~50 words)
#   Clear, concise summary of the chosen action and why, tying together the analysis.
#   Include: the specific action taken (fold/check/call/raise/bet with amount), a brief
#   synthesis of why this is the best decision given all factors analyzed above. This
#   should read as a confident, decisive conclusion from an elite player.
