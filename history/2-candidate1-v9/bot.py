"""Protocol 1.0 entry point. Only request replies are written to stdout."""

import json
import random
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from itertools import combinations
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from pokerbot.cards import canonical, keep_score, score, straight_flush_discard
from pokerbot.strategy import (
    OpponentModel,
    as_cards,
    choose_bet,
    observe_hand,
    sample_equities,
    time_budget_ms,
)


@dataclass(frozen=True)
class State:
    init: Mapping[str, Any]
    hand_id: int = 0
    position: str = ""
    original: tuple[int, ...] = ()
    current: tuple[int, ...] = ()
    original_text: tuple[str, ...] = ()
    opp_discard: int | None = None
    history: tuple[Mapping[str, Any], ...] = ()
    last_request: Mapping[str, Any] | None = None
    applied: Mapping[str, Any] | None = None
    inferred: Mapping[str, Any] | None = None
    inferred_ordinal: int = -1
    mismatches: int = 0
    opponent: OpponentModel = field(default_factory=OpponentModel)
    settled: bool = False


def infer_closing_action(
    state: State, request: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    """Infer only a closing check/call confirmed by public pot and stacks."""
    previous, applied = state.last_request, state.applied
    if previous is None or applied is None:
        return None
    action = applied.get("action")
    street = previous.get("street")
    if action == "raise":
        amount = int(applied["amount"])
        own_cost = amount - int(previous["my_bet"])
        opp_cost = amount - int(previous["opp_bet"])
        closing: Mapping[str, Any] = {
            "street": street,
            "actor": "opp",
            "action": "call",
            "amount": amount,
        }
    elif action == "check":
        # The second check closes the street already; preflop BB's option follows a call.
        last_street = [e for e in state.history if e.get("street") == street]
        if last_street and last_street[-1].get("actor") == "opp":
            return None
        own_cost = opp_cost = 0
        closing = {"street": street, "actor": "opp", "action": "check"}
    else:
        return None
    if (
        int(request["pot"]) != int(previous["pot"]) + own_cost + opp_cost
        or int(request["my_stack"]) != int(previous["my_stack"]) - own_cost
        or int(request["opp_stack"]) != int(previous["opp_stack"]) - opp_cost
    ):
        return None
    return closing


def fallback(req: Mapping[str, Any]) -> dict[str, Any]:
    if req["type"] == "discard_request":
        return {"type": "discard", "card": req["hole_cards"][0]}
    legal = req["legal_actions"]
    action = "check" if "check" in legal else "fold" if "fold" in legal else "call"
    return {"type": "action", "action": action}


def valid(reply: Mapping[str, Any], req: Mapping[str, Any]) -> bool:
    if req["type"] == "discard_request":
        return reply.get("type") == "discard" and reply.get("card") in req["hole_cards"]
    if reply.get("type") != "action" or reply.get("action") not in req["legal_actions"]:
        return False
    if reply.get("action") == "raise":
        amount = reply.get("amount")
        return type(amount) is int and req["min_raise"] <= amount <= req["max_raise"]
    return True


def reduce(state: State, msg: Mapping[str, Any]) -> State:
    kind = msg.get("type")
    if kind == "init":
        return State(init=dict(msg))
    if kind == "new_hand":
        texts = tuple(msg["hole_cards"])
        cards = as_cards(texts)
        return State(
            init=state.init,
            hand_id=int(msg["hand_id"]),
            position=str(msg["seat"]),
            original=cards,
            current=cards,
            original_text=texts,
            mismatches=state.mismatches,
            opponent=state.opponent,
        )
    if kind == "discard_result":
        return replace(
            state,
            current=as_cards(msg["hole_cards"]),
            opp_discard=as_cards([msg["opp_discard"]])[0],
        )
    if kind == "notice" and state.last_request is not None:
        return replace(state, applied={"action": msg.get("applied")})
    if kind == "discard_request":
        inferred = infer_closing_action(state, msg)
        if inferred is not None:
            return replace(
                state,
                history=state.history + (inferred,),
                inferred=inferred,
                inferred_ordinal=len(state.history) + 1,
            )
        return state
    if kind in ("action_request", "hand_result"):
        # Authoritative history prefixes replace, never append or double count.
        history = tuple(msg.get("history", ()))
        mismatch = state.inferred is not None and (
            len(history) <= state.inferred_ordinal
            or any(
                history[state.inferred_ordinal].get(k) != v
                for k, v in state.inferred.items()
            )
        )
        model = state.opponent
        if kind == "hand_result" and not state.settled:
            discarded = msg.get("opp_discard")
            shown = msg.get("opp_hole_cards")
            if (
                msg.get("result") == "showdown"
                and shown is not None
                and discarded is not None
            ):
                triple = as_cards([*shown, discarded])
                revealed_discard = as_cards([discarded])[0]
            else:
                triple = ()
                revealed_discard = None
            model = observe_hand(
                model,
                history,
                state.init,
                state.position,
                triple,
                revealed_discard,
                as_cards(msg.get("board", ())[:3]),
            )
        return replace(
            state,
            history=history,
            inferred=None,
            inferred_ordinal=-1,
            mismatches=state.mismatches + int(mismatch),
            last_request=dict(msg) if kind == "action_request" else state.last_request,
            opponent=model,
            settled=state.settled or kind == "hand_result",
        )
    return state


def royal_keep(
    cards: tuple[int, ...], board: tuple[int, ...]
) -> tuple[int, ...] | None:
    return next(
        (pair for pair in combinations(cards, 2) if score(pair + board) == (8, 14)),
        None,
    )


def decide(
    req: Mapping[str, Any], state: State, table: Mapping[str, float], rng: random.Random
) -> dict[str, Any]:
    board = as_cards(req["board"])
    budget = time_budget_ms(req, state.init, state.hand_id)
    deadline = time.perf_counter() + budget / 1000
    if req["type"] == "discard_request":
        index = straight_flush_discard(state.original, board)
        if index is not None:
            return {"type": "discard", "card": state.original_text[index]}
        equities, count = sample_equities(
            state.original,
            board,
            None,
            state.history,
            rng,
            deadline,
            30,
            state.original,
            state.opponent,
        )
        if count < 4:
            i = max(
                range(3),
                key=lambda j: keep_score(
                    [c for k, c in enumerate(state.original) if k != j], board
                ),
            )
        else:
            i = max(range(3), key=lambda j: equities[j])
        return {"type": "discard", "card": state.original_text[i]}
    if req["street"] == "preflop":
        equity = table[canonical(state.original)]
    else:
        equities, count = sample_equities(
            state.current,
            board,
            state.opp_discard,
            state.history,
            rng,
            deadline,
            36,
            state.original,
            state.opponent,
        )
        if not count and req.get("opp_stack") == 0 and "call" in req["legal_actions"]:
            # The sampler's empty-batch 0.5 is not evidence for paying a shove.
            locked = royal_keep(state.current, board) is not None
            if not locked and req["street"] == "river" and len(board) == 5:
                rank = score(state.current + board)
                if rank[0] == 7:
                    quad = rank[1]
                    locked = sum(c // 4 + 2 == quad for c in board) == 4 and rank[
                        2
                    ] == (13 if quad == 14 else 14)
            return {"type": "action", "action": "call" if locked else "fold"}
        if len(state.current) == 3:
            chosen = max(
                range(3),
                key=lambda j: keep_score(
                    [c for k, c in enumerate(state.current) if k != j], board
                ),
            )
        else:
            chosen = 0
        equity = equities[chosen] if count else 0.5
    return choose_bet(req, equity, rng, state.position, state.opponent)


def main() -> None:
    table = json.loads(
        (Path(__file__).resolve().parent / "assets/preflop.json").read_text(
            encoding="utf-8"
        )
    )
    rng = random.Random()
    state = State(init={})
    recoveries = 0
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(msg, dict):
            continue
        kind = msg.get("type")
        if kind == "match_end":
            break
        old_mismatches = state.mismatches
        state = reduce(state, msg)
        if state.mismatches > old_mismatches and state.mismatches <= 10:
            print(
                "inferred history mismatch; rebuilt from authoritative history",
                file=sys.stderr,
                flush=True,
            )
        if kind not in ("action_request", "discard_request"):
            continue
        reply = fallback(msg)
        try:
            candidate = decide(msg, state, table, rng)
            if valid(candidate, msg):
                reply = candidate
            else:
                raise ValueError("invalid proposed reply")
        except (ValueError, KeyError, IndexError, ArithmeticError, TypeError) as exc:
            recoveries += 1
            if recoveries <= 10:
                print(
                    "decision recovery:",
                    type(exc).__name__,
                    file=sys.stderr,
                    flush=True,
                )
        if kind == "action_request":
            state = replace(state, applied=dict(reply))
        print(json.dumps(reply, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
