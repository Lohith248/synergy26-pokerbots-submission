"""Bounded information-set sampling and simple mixed betting policy.

Each sampled opponent type is jointly weighted by its public actions and discard.
These likelihoods are heuristic priors, not learned frequencies or a solved policy.
"""
import math
import random
import time
from typing import Any, Mapping, Sequence
from pokerbot.cards import card, discard_index, keep_score, score


def action_likelihood(triple: Sequence[int], history: Sequence[Mapping[str, Any]], style: int) -> float:
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
        elif action == "call":
            likelihood = 0.5 + 0.25 * strength
        else:
            likelihood = 0.85 - 0.25 * strength
        weight *= likelihood
    return max(weight, 1e-30)


def discard_probability(triple: Sequence[int], discarded: int, flop: Sequence[int], style: int) -> float:
    if style == 0:
        choice = min(triple, key=lambda c: (c // 4, c % 4))
    elif style == 1:
        # Input order is unobserved, so tied minimum ranks share probability.
        low = min(c // 4 for c in triple)
        return 0.1 / 3 + (0.9 / sum(c // 4 == low for c in triple) if discarded // 4 == low else 0.0)
    elif style == 2:
        choice = triple[discard_index(triple, flop)]
    else:
        return 1 / 3
    return 0.1 / 3 + (0.9 if discarded == choice else 0.0)


def sample_equities(own: Sequence[int], board: Sequence[int], opp_discard: int | None,
                    history: Sequence[Mapping[str, Any]], rng: random.Random,
                    deadline: float, limit: int, original: Sequence[int] = ()) -> tuple[list[float], int]:
    """Compare all keeps on identical scenarios; no revealed discard before it exists."""
    known = set(own) | set(original) | set(board)
    if opp_discard is not None:
        known.add(opp_discard)
    deck = [c for c in range(52) if c not in known]
    keeps = [[c for j, c in enumerate(own) if j != i] for i in range(3)] if len(own) == 3 else [list(own)]
    totals = [0.0] * len(keeps)
    weight_sum = 0.0
    count = 0
    while count < limit and time.perf_counter() < deadline:
        n_opp = 3 if opp_discard is None else 2
        need = n_opp + 5 - len(board)
        draw = rng.sample(deck, need)
        opp = draw[:n_opp]
        triple = opp if opp_discard is None else opp + [opp_discard]
        style = rng.randrange(4)
        weight = action_likelihood(triple, history, style)
        if opp_discard is None:
            # The simulated opponent sees only its own triple and the flop.
            if style == 0:
                drop = min(range(3), key=lambda i: (opp[i] // 4, opp[i] % 4))
            elif style == 1:
                drop = min(range(3), key=lambda i: opp[i] // 4)
            elif style == 2:
                drop = discard_index(opp, board[:3])
            else:
                drop = rng.randrange(3)
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


def time_budget_ms(req: Mapping[str, Any], init: Mapping[str, Any], hand_id: int) -> float:
    bank = max(0.0, float(req.get("time_left_ms", init.get("time_bank_ms", 30000))))
    remaining = max(1, int(init.get("total_hands", 200)) - hand_id + 1)
    response = max(0.0, float(init.get("per_response_ms", 5000)) - 20.0)
    return min(7.0, response, bank * 0.5 / (remaining * 5), bank * 0.1)


def choose_bet(req: Mapping[str, Any], equity: float, rng: random.Random, position: str) -> dict[str, Any]:
    legal = req["legal_actions"]
    pot = int(req["pot"])
    call = int(req["to_call"])
    street = req["street"]
    equity = max(0.02, min(0.98, equity))
    # Early-street equity is discounted to account for future bets and realization.
    realization = {"preflop": 0.88, "flop": 0.89, "turn": 0.94, "river": 1.0}[street]
    if street == "preflop":
        realization += 0.025 if position == "button" else -0.015
    if position == "button" and street != "preflop":
        realization += 0.025
    adjusted = equity * realization
    if "raise" in legal:
        minimum, maximum = int(req["min_raise"]), int(req["max_raise"])
        amount = max(minimum, min(maximum, int(req["opp_bet"]) + max(2, round(0.65 * (pot + call)))))
        cost = amount - int(req["my_bet"])
        # Fold probability and call equity are explicit, approximate response models.
        fold_prob = min(0.48, max(0.08, 0.28 + 0.10 * (cost / max(1, pot) - 0.5)))
        called_equity = max(0.01, equity - 0.09)
        raise_ev = fold_prob * pot + (1 - fold_prob) * (called_equity * (pot + 2 * cost) - cost)
        call_ev = adjusted * (pot + call) - call if call else adjusted * pot
        value = equity > (0.66 if street == "preflop" else 0.67)
        bluff = equity < 0.48 and rng.random() < (0.08 if call == 0 else 0.025)
        if (value and raise_ev > call_ev * 0.82) or (bluff and cost < pot):
            return {"type": "action", "action": "raise", "amount": amount}
    if "check" in legal:
        return {"type": "action", "action": "check"}
    if "call" in legal and adjusted * (pot + call) >= call:
        return {"type": "action", "action": "call"}
    return {"type": "action", "action": "fold"}


def as_cards(texts: Sequence[str]) -> tuple[int, ...]:
    return tuple(card(x) for x in texts)
