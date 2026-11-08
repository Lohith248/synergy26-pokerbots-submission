"""Bounded information-set sampling and simple mixed betting policy.

Each sampled opponent type is jointly weighted by its public actions and discard.
These likelihoods are heuristic priors, not learned frequencies or a solved policy.
"""

import math
import random
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from pokerbot.cards import card, keep_score, score

EQUITY_ROLLOUT_VARIANTS = 3


@dataclass(frozen=True)
class OpponentModel:
    """Leg-local observations; style evidence is from selected showdowns only."""

    fold_opportunities: int = 0
    folds: int = 0
    raise_opportunities: int = 0
    raises: int = 0
    style_evidence: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    revealed_discards: int = 0


def style_probabilities(model: OpponentModel) -> tuple[float, ...]:
    # Eighteen prior observations plus a 50% uniform mixture limit selection bias.
    total = 18.0 + sum(model.style_evidence)
    return tuple(
        0.5 / 6 + 0.5 * (3.0 + value) / total for value in model.style_evidence
    )


def observe_hand(
    model: OpponentModel,
    history: Sequence[Mapping[str, Any]],
    init: Mapping[str, Any],
    position: str,
    revealed_triple: Sequence[int],
    discarded: int | None,
    flop: Sequence[int],
) -> OpponentModel:
    """Update once from a complete authoritative history; folded cards are censored."""
    small = int(init.get("small_blind", 1))
    big = int(init.get("big_blind", 2))
    start = int(init.get("starting_stack", 200))
    bets = {
        "me": small if position == "button" else big,
        "opp": big if position == "button" else small,
    }
    stacks = {actor: start - amount for actor, amount in bets.items()}
    street = "preflop"
    raises = 1
    fold_opportunities, folds = model.fold_opportunities, model.folds
    raise_opportunities, raise_count = model.raise_opportunities, model.raises
    for event in history:
        current_street = str(event["street"])
        if current_street != street:
            street = current_street
            bets = {"me": 0, "opp": 0}
            raises = 0
        actor = str(event["actor"])
        other = "opp" if actor == "me" else "me"
        action = event["action"]
        if actor == "opp":
            if bets[other] > bets[actor]:
                fold_opportunities += 1
                folds += int(action == "fold")
            max_raise = min(bets[actor] + stacks[actor], bets[other] + stacks[other])
            if raises < 4 and max_raise > bets[other]:
                raise_opportunities += 1
                raise_count += int(action == "raise")
        if action in ("call", "raise"):
            amount = int(event["amount"])
            stacks[actor] -= amount - bets[actor]
            bets[actor] = amount
            if action == "raise":
                raises += 1
    evidence = model.style_evidence
    revealed_count = model.revealed_discards
    if len(revealed_triple) == 3 and discarded is not None and len(flop) == 3:
        likelihoods = [
            p * discard_probability(revealed_triple, discarded, flop, i)
            for i, p in enumerate(style_probabilities(model))
        ]
        total = sum(likelihoods)
        if total > 0 and math.isfinite(total):
            evidence = tuple(
                old + likelihood / total
                for old, likelihood in zip(evidence, likelihoods)
            )
            revealed_count += 1
    return replace(
        model,
        fold_opportunities=fold_opportunities,
        folds=folds,
        raise_opportunities=raise_opportunities,
        raises=raise_count,
        style_evidence=evidence,
        revealed_discards=revealed_count,
    )


def modeled_choices(
    triple: Sequence[int], flop: Sequence[int], style: int, rollout_variant: int = 0
) -> tuple[int, ...]:
    """Return tied choices before uniform tie-breaking over the hidden input order."""
    if style == 0:
        return (min(range(3), key=lambda i: (triple[i] // 4, triple[i] % 4)),)
    if style == 1:
        low = min(c // 4 for c in triple)
        return tuple(i for i, c in enumerate(triple) if c // 4 == low)
    if style == 2:
        made_values = [
            score([c for j, c in enumerate(triple) if i != j] + list(flop))
            for i in range(3)
        ]
        best_made = max(made_values)
        return tuple(i for i, value in enumerate(made_values) if value == best_made)
    if style == 3:

        def draw_value(i: int) -> float:
            cs = [c for j, c in enumerate(triple) if i != j] + list(flop)
            suits = max(sum(c % 4 == s for c in cs) for s in range(4))
            ranks = {c // 4 + 2 for c in cs}
            if 14 in ranks:
                ranks.add(1)
            connected = max(
                sum(r in ranks for r in range(low, low + 5)) for low in range(1, 11)
            )
            return 2 * suits + connected + keep_score(cs[:2], flop) * 0.01

        draw_values = [draw_value(i) for i in range(3)]
        best_draw = max(draw_values)
        return tuple(i for i, value in enumerate(draw_values) if value == best_draw)
    if style == 4:
        # A public-information-derived stream; hypothetical hands never exclude our actual hidden cards.
        seed = (
            sum((c + 1) * (53**i) for i, c in enumerate(sorted(triple) + sorted(flop)))
            + (53**6) * rollout_variant
        )
        local = random.Random(seed)
        deck = [c for c in range(52) if c not in set(triple) | set(flop)]
        totals = [0.0, 0.0, 0.0]
        for _ in range(4):
            draw = local.sample(deck, 4)
            board = list(flop) + draw[2:]
            other = score(draw[:2] + board)
            for i in range(3):
                own = score([c for j, c in enumerate(triple) if i != j] + board)
                totals[i] += (own > other) + 0.5 * (own == other)
        best_equity = max(totals)
        return tuple(i for i, value in enumerate(totals) if value == best_equity)
    raise ValueError("no deterministic choice for noisy style")


def action_likelihood(
    triple: Sequence[int],
    history: Sequence[Mapping[str, Any]],
    style: int,
    model: OpponentModel,
) -> float:
    ranks = sorted((c // 4 + 2 for c in triple), reverse=True)
    strength = (sum(ranks) - 6) / 36 + (0.18 if len(set(ranks)) < 3 else 0)
    weight = 1.0
    for event in history:
        if event.get("actor") != "opp":
            continue
        action = event.get("action")
        # All legal events retain positive support, including unusual bets.
        if action == "raise":
            likelihood = 0.2 + 0.65 * min(1.0, strength + (0.12 if style == 2 else 0.0))
            aggression = (8.0 + model.raises) / (25.0 + model.raise_opportunities)
            likelihood *= 1 + 0.6 * (0.32 - aggression) * (2 * strength - 1)
        elif action == "call":
            likelihood = 0.5 + 0.25 * strength
        else:
            likelihood = 0.85 - 0.25 * strength
        weight *= likelihood
    return max(weight, 1e-30)


def discard_probability(
    triple: Sequence[int], discarded: int, flop: Sequence[int], style: int
) -> float:
    if style == 5:
        return 1 / 3
    variants = EQUITY_ROLLOUT_VARIANTS if style == 4 else 1
    probability = 0.0
    for variant in range(variants):
        choices = modeled_choices(triple, flop, style, variant)
        if any(triple[i] == discarded for i in choices):
            probability += 1 / len(choices)
    return 0.1 / 3 + 0.9 * probability / variants


def sample_equities(
    own: Sequence[int],
    board: Sequence[int],
    opp_discard: int | None,
    history: Sequence[Mapping[str, Any]],
    rng: random.Random,
    deadline: float,
    limit: int,
    original: Sequence[int] = (),
    model: OpponentModel | None = None,
) -> tuple[list[float], int]:
    """Compare all keeps on identical scenarios; no revealed discard before it exists."""
    model = model if model is not None else OpponentModel()
    known = set(own) | set(original) | set(board)
    if opp_discard is not None:
        known.add(opp_discard)
    deck = [c for c in range(52) if c not in known]
    keeps = (
        [[c for j, c in enumerate(own) if j != i] for i in range(3)]
        if len(own) == 3
        else [list(own)]
    )
    totals = [0.0] * len(keeps)
    weight_sum = 0.0
    count = 0
    while count < limit and time.perf_counter() < deadline:
        n_opp = 3 if opp_discard is None else 2
        need = n_opp + 5 - len(board)
        draw = rng.sample(deck, need)
        opp = draw[:n_opp]
        triple = opp if opp_discard is None else opp + [opp_discard]
        style = rng.randrange(6)
        weight = (
            action_likelihood(triple, history, style, model)
            * 6
            * style_probabilities(model)[style]
        )
        if opp_discard is None:
            # The simulated opponent sees only its own triple and the flop.
            if style == 5 or rng.random() < 0.1:
                drop = rng.randrange(3)
            else:
                variant = rng.randrange(EQUITY_ROLLOUT_VARIANTS) if style == 4 else 0
                choices = modeled_choices(opp, board[:3], style, variant)
                drop = choices[rng.randrange(len(choices))]
            opp = [c for i, c in enumerate(opp) if i != drop]
        else:
            weight *= discard_probability(triple, opp_discard, board[:3], style)
        final_board = list(board) + draw[n_opp:]
        other = score(opp + final_board)
        for i, keep in enumerate(keeps):
            mine = score(keep + final_board)
            totals[i] += weight * ((mine > other) + 0.5 * (mine == other))
        count += 1
        weight_sum += weight
    if not weight_sum or not math.isfinite(weight_sum):
        return [0.5] * len(keeps), count
    return [v / weight_sum for v in totals], count


def time_budget_ms(
    req: Mapping[str, Any], init: Mapping[str, Any], hand_id: int
) -> float:
    bank = max(0.0, float(req.get("time_left_ms", init.get("time_bank_ms", 30000))))
    remaining = max(1, int(init.get("total_hands", 200)) - hand_id + 1)
    response = max(0.0, float(init.get("per_response_ms", 5000)) - 20.0)
    return min(7.0, response, bank * 0.5 / (remaining * 5), bank * 0.1)


def called_pot(pot: int, cost: int, call: int) -> int:
    """Pot after our raise and an opponent call, including the existing wager."""
    return pot + 2 * cost - call


def choose_bet(
    req: Mapping[str, Any],
    equity: float,
    rng: random.Random,
    position: str,
    model: OpponentModel | None = None,
) -> dict[str, Any]:
    model = model if model is not None else OpponentModel()
    legal = req["legal_actions"]
    pot = int(req["pot"])
    call = int(req["to_call"])
    street = req["street"]
    if req.get("opp_stack") == 0 and "call" in legal:
        # An all-in call buys the showdown, even when cards or discards remain.
        action = "call" if equity >= call / (pot + call) else "fold"
        return {"type": "action", "action": action}
    equity = max(0.02, min(0.98, equity))
    # Early-street equity is discounted to account for future bets and realization.
    realization = {"preflop": 0.88, "flop": 0.89, "turn": 0.94, "river": 1.0}[street]
    if street == "preflop":
        realization += 0.025 if position == "button" else -0.015
    if position == "button" and street not in ("preflop", "river"):
        realization += 0.025
    adjusted = equity * realization
    if "raise" in legal:
        minimum, maximum = int(req["min_raise"]), int(req["max_raise"])
        amount = max(
            minimum,
            min(maximum, int(req["opp_bet"]) + max(2, round(0.65 * (pot + call)))),
        )
        cost = amount - int(req["my_bet"])
        # Fold probability and call equity are explicit, approximate response models.
        tendency = (7.0 + model.folds) / (25.0 + model.fold_opportunities)
        fold_prob = min(
            0.48,
            max(0.08, 0.5 * 0.28 + 0.5 * tendency + 0.10 * (cost / max(1, pot) - 0.5)),
        )
        called_equity = max(0.01, equity - 0.09)
        raise_ev = fold_prob * pot + (1 - fold_prob) * (
            called_equity * called_pot(pot, cost, call) - cost
        )
        call_ev = adjusted * (pot + call) - call if call else adjusted * pot
        value = equity > (0.66 if street == "preflop" else 0.67)
        bluff_rate = (0.08 if call == 0 else 0.025) + 0.15 * (tendency - 0.28)
        bluff = equity < 0.48 and rng.random() < max(0.01, min(0.14, bluff_rate))
        if (value and raise_ev > call_ev * 0.82) or (bluff and cost < pot):
            return {"type": "action", "action": "raise", "amount": amount}
    if "check" in legal:
        return {"type": "action", "action": "check"}
    if "call" in legal and adjusted * (pot + call) >= call:
        return {"type": "action", "action": "call"}
    return {"type": "action", "action": "fold"}


def as_cards(texts: Sequence[str]) -> tuple[int, ...]:
    return tuple(card(x) for x in texts)
