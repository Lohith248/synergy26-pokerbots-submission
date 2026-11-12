import sys
import json
import time
import math
import random
import base64
import gc
import zlib
import struct
import itertools
import os

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

try:
    import numpy as np
    HAVE_NP = True
except Exception:
    np = None
    HAVE_NP = False

DEBUG = False

PARAMS = {
    "max_reply_s": 0.8,
    "clock_share": 0.25,
    "clock_decisions_per_hand": 2.5,
    "emergency_floor_ms": 4000,
    "emergency_ms_per_hand": 15,
    "fallback_call_frac": 0.1,
    "kd_flush_draw": 0.75,
    "kd_nut_flush_draw": 0.12,
    "kd_backdoor": 0.08,
    "kd_oesd": 0.7,
    "kd_gutshot": 0.3,
    "kd_overcard": 0.06,
    "kd_pocket": 0.1,
    "kd_ace": 0.04,
    "keep_beta": 6.0,
    "discard_samples": 3000,
    "discard_batch": 400,
    "discard_tie": 0.003,
    "rm_alpha": 8.0,
    "rm_floor": 0.015,
    "rm_aggr_prior": (0.4, 0.2, 0.1, 0.06),
    "rm_cont_base": 0.78,
    "rm_cont_slope": 0.42,
    "rm_size_shift": 0.16,
    "eq_flop_samples": 2000,
    "eq_batch": 400,
    "eq_min_samples": 400,
    "eq_turn_epochs": 2,
    "eq_cont_alpha": 12.0,
    "pf_open_cut": 0.25,
    "pf_limp_cut": 0.05,
    "pf_open_size": 4,
    "pf_open_size_loose": 5,
    "pf_loose_fold": 0.25,
    "pf_iso_cut": 0.70,
    "pf_iso_size": 6,
    "pf_call_margin": 0.015,
    "pf_oop_margin": 0.02,
    "pf_big_margin": 0.01,
    "pf_shove_margin": 0.045,
    "pf_shove_rate": 0.6,
    "pf_big_frac": 0.4,
    "pf_value_eq": 0.63,
    "pf_jam_eq": 0.68,
    "pf_value_freq": 0.85,
    "pf_raise_mult": 3.0,
    "pf_bluff_freq": 0.10,
    "pf_bluff_fold": 0.40,
    "pf_prior_small": (0.35, 0.15, 0.08, 0.06, 0.25),
    "pf_prior_big": (0.12, 0.10, 0.10, 0.10, 0.10),
    "pf_size_ref": (5.0, 14.0, 30.0, 60.0, 6.0),
    "pf_fold_prior": 0.45,
    "opp_prior_n": 7.0,
    "agg_prior": 0.35,
    "agg_min_n": 20,
    "rm_floor_min": 0.004,
    "rm_floor_max": 0.08,
    "bluff_prior": 0.20,
    "bluff_prior_n": 6.0,
    "bluff_pct": 0.45,
    "static_min_n": 30,
    "static_share": 0.95,
    "static_margin": 0.02,
    "alpha_cap": 1.15,
    "alpha_sep_ref": 0.3,
    "keep_prior_rate": 0.80,
    "beta_cap": 1.5,
    "pf_steal_base": 0.5,
    "pf_steal_slope": 1.0,
    "bet_sizes": (0.33, 0.5, 0.75, 1.0, 1.5),
    "fold_prior": {
        "flop": (0.28, 0.36, 0.42, 0.48),
        "turn": (0.32, 0.40, 0.46, 0.52),
        "river": (0.34, 0.44, 0.50, 0.55),
    },
    "fold_edges": (0.4, 0.8, 1.2),
    "fold_raise_mult": 0.75,
    "sel_floor": 0.18,
    "real_ip": {"flop": 0.95, "turn": 0.97, "river": 1.0},
    "real_oop": {"flop": 0.88, "turn": 0.92, "river": 1.0},
    "reraise_prob": 0.12,
    "rr_range": 0.25,
    "mix_eps": 0.03,
    "spr_shove": 1.5,
    "max_shove_spr": 2.0,
    "mdf_slack": 0.02,
    "mdf_aggr": 0.45,
    "big_call_tax": 0.02,
    "big_call_min": 33,
    "big_call_odds": 0.3,
    "cbet_freq": 0.75,
    "cbet_fold_min": 0.30,
    "cbet_tol": 0.10,
    "rr_read_min": 2,
    "rr_read_prior": 0.7,
    "rr_read_cut": 0.68,
    "rr_read_gain": 0.8,
    "rr_read_cap": 0.15,
    "rr_sel_n": 12,
    "rr_sel_rate": 0.10,
    "rr_sel_pen": 0.05,
    "rr_nut_turn_cap": 0.02,
    "rm_trap": 0.2,
}

RANKS = "23456789TJQKA"
STREETS = ("preflop", "flop", "turn", "river")
STREET_WEIGHT = {"preflop": 0.2, "flop": 1.0, "discard": 1.0, "turn": 1.2, "river": 1.0}

LAST_REPLY_RESERVE_MS = 50
_LOG_BUDGET = [8000]


def log(*parts):
    # stderr only, capped so a match never produces more than a few KB
    if not DEBUG or _LOG_BUDGET[0] <= 0:
        return
    text = " ".join(str(p) for p in parts) + "\n"
    _LOG_BUDGET[0] -= len(text)
    try:
        sys.stderr.write(text)
        sys.stderr.flush()
    except Exception:
        pass


def send(obj):
    # the only place that writes to stdout
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def rank_of(card):
    return RANKS.index(card[0])


def as_int(x, default=0):
    try:
        if isinstance(x, bool):
            return default
        return int(x)
    except (TypeError, ValueError, OverflowError):
        return default


SUITS = "shdc"


def parse_card(card):
    # card int is rank * 4 + suit, rank 0..12 for 2..A, suit order s h d c
    return RANKS.index(card[0]) * 4 + SUITS.index(card[1])


def card_str(c):
    return RANKS[c >> 2] + SUITS[c & 3]


# Hand score: category in bits 20+, then five 4-bit rank fields (0..12).
# Categories: 0 high card .. 8 straight flush, same order as the engine tuples.

def _build_tables():
    hb = [0] * 8192
    top5 = [0] * 8192
    sh = [0] * 8192
    for m in range(1, 8192):
        ranks = [r for r in range(12, -1, -1) if m >> r & 1]
        hb[m] = ranks[0]
        enc = 0
        for i in range(5):
            enc = (enc << 4) | (ranks[i] if i < len(ranks) else 0)
        top5[m] = enc
        for high in range(12, 3, -1):
            window = 0x1F << (high - 4)
            if m & window == window:
                sh[m] = high + 2
                break
        else:
            if m & 0x100F == 0x100F:
                sh[m] = 5
    return hb, top5, sh


_HB, _TOP5, _SH = _build_tables()
STRAIGHT_HIGH = _SH
TOP5 = _TOP5

if HAVE_NP:
    _HB_NP = np.array(_HB, dtype=np.int64)
    _TOP5_NP = np.array(_TOP5, dtype=np.int64)
    _SH_NP = np.array(_SH, dtype=np.int64)


def eval_one(cards):
    """Score of 5 to 7 card ints; same encoding as eval_batch."""
    cnt = [0] * 13
    scnt = [0, 0, 0, 0]
    smask = [0, 0, 0, 0]
    mask = 0
    for c in cards:
        r = c >> 2
        s = c & 3
        cnt[r] += 1
        scnt[s] += 1
        smask[s] |= 1 << r
        mask |= 1 << r
    m2 = m3 = m4 = 0
    for r in range(13):
        n = cnt[r]
        if n > 1:
            if n == 2:
                m2 |= 1 << r
            elif n == 3:
                m3 |= 1 << r
            else:
                m4 |= 1 << r
    fm = 0
    for s in range(4):
        if scnt[s] >= 5:
            fm = smask[s]
    if fm:
        v = _SH[fm]
        if v:
            return (8 << 20) | ((v - 2) << 16)
    if m4:
        q = _HB[m4]
        return (7 << 20) | (q << 16) | (_HB[mask & ~(1 << q)] << 12)
    if m3:
        t = _HB[m3]
        pc = (m3 & ~(1 << t)) | m2
        if pc:
            return (6 << 20) | (t << 16) | (_HB[pc] << 12)
    if fm:
        return (5 << 20) | _TOP5[fm]
    v = _SH[mask]
    if v:
        return (4 << 20) | ((v - 2) << 16)
    if m3:
        t = _HB[m3]
        return (3 << 20) | (t << 16) | ((_TOP5[mask & ~(1 << t)] >> 4) & 0xFF00)
    if m2:
        p = _HB[m2]
        rest = m2 & ~(1 << p)
        if rest:
            p2 = _HB[rest]
            k = _HB[mask & ~(1 << p) & ~(1 << p2)]
            return (2 << 20) | (p << 16) | (p2 << 12) | (k << 8)
        return (1 << 20) | (p << 16) | ((_TOP5[mask & ~(1 << p)] >> 4) & 0xFFF0)
    return _TOP5[mask]


def eval_batch(H):
    """Scores for an (N, k) array of card ints, k in 5..7."""
    if not HAVE_NP:
        return [eval_one(row) for row in H]
    H = np.asarray(H, dtype=np.int64)
    rank = H >> 2
    suit = H & 3
    bits = np.left_shift(1, rank)
    mask = np.bitwise_or.reduce(bits, axis=1)
    # Three bits per rank or suit hold its count without overflow (at most seven cards).
    rank_shift = 3 * rank
    rank_counts = np.left_shift(1, rank_shift).sum(axis=1)
    same = (rank_counts[:, None] >> rank_shift) & 7
    m2 = np.bitwise_or.reduce(np.where(same == 2, bits, 0), axis=1)
    m3 = np.bitwise_or.reduce(np.where(same == 3, bits, 0), axis=1)
    m4 = np.bitwise_or.reduce(np.where(same == 4, bits, 0), axis=1)
    suit_shift = 3 * suit
    suit_counts = np.left_shift(1, suit_shift).sum(axis=1)
    ssame = (suit_counts[:, None] >> suit_shift) & 7
    fm = np.bitwise_or.reduce(np.where(ssame >= 5, bits, 0), axis=1)

    score = _TOP5_NP[mask]

    # one pair
    p = _HB_NP[m2]
    rest = mask & ~np.left_shift(1, p)
    pair = (1 << 20) | (p << 16) | ((_TOP5_NP[rest] >> 4) & 0xFFF0)
    score = np.where(m2 != 0, pair, score)

    # two pair, the best two of up to three pairs
    p2 = _HB_NP[m2 & ~np.left_shift(1, p)]
    k = _HB_NP[rest & ~np.left_shift(1, p2)]
    two = (2 << 20) | (p << 16) | (p2 << 12) | (k << 8)
    score = np.where((m2 & (m2 - 1)) != 0, two, score)

    # trips
    t = _HB_NP[m3]
    rest3 = mask & ~np.left_shift(1, t)
    trips = (3 << 20) | (t << 16) | ((_TOP5_NP[rest3] >> 4) & 0xFF00)
    score = np.where(m3 != 0, trips, score)

    # straight
    sv = _SH_NP[mask]
    score = np.where(sv != 0, (4 << 20) | ((sv - 2) << 16), score)

    # flush
    score = np.where(fm != 0, (5 << 20) | _TOP5_NP[fm], score)

    # full house, the second trip counts as the pair
    pc = (m3 & ~np.left_shift(1, t)) | m2
    full = (6 << 20) | (t << 16) | (_HB_NP[pc] << 12)
    score = np.where((m3 != 0) & (pc != 0), full, score)

    # quads
    q = _HB_NP[m4]
    kq = _HB_NP[mask & ~np.left_shift(1, q)]
    quads = (7 << 20) | (q << 16) | (kq << 12)
    score = np.where(m4 != 0, quads, score)

    # straight flush
    fv = _SH_NP[fm]
    score = np.where(fv != 0, (8 << 20) | ((fv - 2) << 16), score)
    return score


class Clock:
    """Per-decision time budget derived from the remaining bank."""

    def __init__(self):
        self.bank_ms = 30000
        self.per_response_ms = 5000
        self.total_hands = 200
        self.hand_id = 1
        self.time_left_ms = 30000

    def configure(self, msg):
        self.bank_ms = max(1, as_int(msg.get("time_bank_ms"), 30000))
        self.per_response_ms = max(1, as_int(msg.get("per_response_ms"), 5000))
        self.total_hands = max(1, as_int(msg.get("total_hands"), 200))
        self.time_left_ms = self.bank_ms
        self.hand_id = 1

    def observe(self, msg):
        left = msg.get("time_left_ms")
        if isinstance(left, (int, float)) and not isinstance(left, bool) and left == left:
            self.time_left_ms = left
        hand_id = as_int(msg.get("hand_id"))
        if hand_id > 0:
            self.hand_id = hand_id

    def hands_left(self):
        return max(1, self.total_hands - self.hand_id + 1)

    def emergency(self):
        floor = max(PARAMS["emergency_floor_ms"],
                    PARAMS["emergency_ms_per_hand"] * self.hands_left())
        return self.time_left_ms < floor

    def budget(self, street="flop"):
        """Seconds available for the current decision; 0 means table-only."""
        if self.emergency():
            return 0.0
        decisions = self.hands_left() * PARAMS["clock_decisions_per_hand"]
        share = PARAMS["clock_share"] * (self.time_left_ms / 1000.0) / decisions
        cap = min(PARAMS["max_reply_s"], 0.5 * self.per_response_ms / 1000.0)
        return min(cap, share * STREET_WEIGHT.get(street, 1.0))

    def deadline(self, street="flop"):
        return time.perf_counter() + self.budget(street)


def parse_history(history, my_seat="button", stack=200, small_blind=1, big_blind=2):
    """Replay the voluntary actions from the blinds and describe each one."""
    me = 0 if my_seat == "button" else 1
    committed = [small_blind, big_blind]
    bets = [small_blind, big_blind]
    street = "preflop"
    raises = 1
    actions = []
    for entry in history or []:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("action")
        who = {"me": me, "opp": 1 - me}.get(entry.get("actor"))
        if who is None or kind not in ("fold", "check", "call", "raise"):
            continue
        if entry.get("street") in STREETS and entry["street"] != street:
            street = entry["street"]
            bets = [0, 0]
            raises = 0
        own, other = bets[who], bets[1 - who]
        pot_before = sum(committed)
        amount = entry.get("amount")
        if kind == "call":
            to = as_int(amount, other)
        elif kind == "raise":
            to = as_int(amount, other + big_blind)
        else:
            to = own
        add = max(0, to - own) if kind in ("call", "raise") else 0
        add = min(add, stack - committed[who])
        to = own + add
        bets[who] = to
        committed[who] += add
        if kind == "raise":
            raises += 1
        actions.append({
            "street": street,
            "actor": "me" if who == me else "opp",
            "action": kind,
            "to": to,
            "added": add,
            "to_call": max(0, other - own),
            "pot_before": pot_before,
            "frac": add / pot_before if kind == "raise" and pot_before else 0.0,
            "is_raise": kind == "raise",
            "is_bet": kind == "raise" and other == 0,
            "is_allin": kind in ("call", "raise") and committed[who] >= stack,
            "raise_no": raises,
        })
    return ParsedHistory(actions, committed, bets, street, raises)


class ParsedHistory:
    def __init__(self, actions, committed, bets, street, raises):
        self.actions = actions
        self.committed = committed
        self.bets = bets
        self.street = street
        self.raises = raises

    @property
    def pot(self):
        return sum(self.committed)


class HandState:
    def __init__(self, hand_id, seat, hole):
        self.hand_id = hand_id
        self.seat = seat
        self.hole = list(hole)
        self.board = []
        self.pot = 3
        self.street = "preflop"
        self.my_discard = None
        self.opp_discard = None

    def observe(self, req):
        board = req.get("board")
        if isinstance(board, list):
            self.board = [c for c in board if isinstance(c, str)]
        if req.get("street") in STREETS:
            self.street = req["street"]
        self.pot = as_int(req.get("pot"), self.pot)
        hole = req.get("hole_cards")
        if isinstance(hole, list) and hole:
            self.hole = [c for c in hole if isinstance(c, str)]

    def on_discard(self, msg):
        self.my_discard = msg.get("my_discard")
        self.opp_discard = msg.get("opp_discard")
        hole = msg.get("hole_cards")
        if isinstance(hole, list) and hole:
            self.hole = [c for c in hole if isinstance(c, str)]


class OppModel:
    """Running opponent statistics with pseudo-count priors."""

    def __init__(self):
        self.pf_opps = [0] * 5
        self.pf_small = [0] * 5
        self.pf_big = [0] * 5
        self.pf_fold = [0, 0]
        self.pf_fold3 = [0, 0]
        self.agg = [0, 0]
        self.fold_c = {}
        self.hands = 0
        self.pf_acted = 0
        self.vpip = 0
        self.pfr = 0
        self.limps = 0
        self.pf_allin = [0] * 5
        self.bet_chk = [0, 0]
        self.face = [0, 0]
        self.chk_raise = [0, 0]
        self.bet_frac = [0.0, 0]
        self.kinds = {"fold": 0, "check": 0, "call": 0, "raise": 0}
        self.sd_agg = [0, 0.0]
        self.sd_pas = [0, 0.0]
        self.keep_hits = [0, 0]
        self.bluffs = [0, 0]
        self.rr_sd = [0, 0.0]  # his raises over our postflop bets that showed down: count, pct sum

    @staticmethod
    def bucket(ratio):
        return sum(1 for e in PARAMS["fold_edges"] if ratio >= e)

    def update(self, msg, seat, stack):
        parsed = parse_history(msg.get("history"), seat, stack)
        opp_bb = seat == "button"
        prev = None
        first = True
        checked = set()
        for a in parsed.actions:
            if a["actor"] == "opp":
                self.kinds[a["action"]] += 1
                if a["street"] == "preflop":
                    k = a["raise_no"] - 1 - (1 if a["is_raise"] else 0)
                    key = 4 if (k <= 0 and opp_bb) else min(max(k, 0), 3)
                    self.pf_opps[key] += 1
                    if first:
                        first = False
                        self.pf_acted += 1
                        if a["action"] in ("call", "raise"):
                            self.vpip += 1
                        if a["is_raise"]:
                            self.pfr += 1
                        elif a["action"] == "call" and k <= 0 and not opp_bb:
                            self.limps += 1
                    if a["is_allin"] and a["is_raise"]:
                        self.pf_allin[key] += 1
                    if a["is_raise"]:
                        big = a["is_allin"] or a["to"] >= PARAMS["pf_big_frac"] * stack
                        (self.pf_big if big else self.pf_small)[key] += 1
                else:
                    self.agg[1] += 1
                    if a["is_raise"]:
                        self.agg[0] += 1
                        self.bet_frac[0] += min(3.0, a["frac"])
                        self.bet_frac[1] += 1
                    if a["to_call"] <= 0:
                        self.bet_chk[1] += 1
                        if a["is_raise"]:
                            self.bet_chk[0] += 1
                        else:
                            checked.add(a["street"])
                    else:
                        self.face[1] += 1
                        if a["is_raise"]:
                            self.face[0] += 1
                        if a["street"] in checked:
                            self.chk_raise[1] += 1
                            if a["is_raise"]:
                                self.chk_raise[0] += 1
                if prev is not None and prev["actor"] == "me" and prev["is_raise"] \
                        and prev["street"] == a["street"]:
                    folded = 1 if a["action"] == "fold" else 0
                    if a["street"] == "preflop":
                        self.pf_fold[0] += folded
                        self.pf_fold[1] += 1
                        if prev["raise_no"] >= 3:
                            self.pf_fold3[0] += folded
                            self.pf_fold3[1] += 1
                    else:
                        b = self.bucket(prev["frac"])
                        cell = self.fold_c.setdefault((a["street"], not prev["is_bet"], b), [0, 0])
                        cell[0] += folded
                        cell[1] += 1
            prev = a
        self.hands += 1
        try:
            self.showdown(msg, parsed)
        except Exception as exc:
            log("showdown stats error", repr(exc))

    def showdown(self, msg, parsed):
        """Learn how honest his actions and discards are from the cards he showed."""
        hole = msg.get("opp_hole_cards")
        gone = msg.get("opp_discard")
        board = msg.get("board")
        if not (isinstance(hole, list) and len(hole) == 2 and isinstance(gone, str)
                and isinstance(board, list) and len(board) >= 3):
            return
        three = [parse_card(c) for c in hole] + [parse_card(gone)]
        flop = [parse_card(c) for c in board[:3]]
        if len(set(three) | set(flop)) != 6:
            return
        cls = class_of(three)
        if cls >= 0:
            pct = PF_PCT[cls]
            for a in parsed.actions:
                if a["actor"] == "opp" and a["street"] == "preflop" and a["action"] != "fold":
                    side = self.sd_agg if a["is_raise"] else self.sd_pas
                    side[0] += 1
                    side[1] += pct
        self.bet_honesty(hole, board, parsed)
        ks = keep_scores([three], flop)[0]
        top = max(range(3), key=lambda i: ks[i])
        self.keep_hits[1] += 1
        if top == 2:
            self.keep_hits[0] += 1

    def bet_honesty(self, hole, board, parsed):
        """Count his showdown bets that were made with a clearly below-median hand."""
        if not HAVE_NP or len(board) < 5:
            return
        pair = [parse_card(c) for c in hole]
        cards = [parse_card(c) for c in board[:5]]
        seen = set()
        rr_done = False
        for a in parsed.actions:
            if (a["actor"] != "opp" or not a["is_raise"] or a["street"] in seen
                    or a["street"] == "preflop"):
                continue
            seen.add(a["street"])
            bd = cards[:{"flop": 3, "turn": 4, "river": 5}[a["street"]]]
            dead = set(pair) | set(bd)
            live = np.array([c for c in range(52) if c not in dead], dtype=np.int64)
            i, j = np.triu_indices(len(live), 1)
            rows = np.concatenate([np.stack([live[i], live[j]], axis=1), _rows(bd, len(i))],
                                  axis=1)
            theirs = eval_one(pair + bd)
            sc = eval_batch(rows)
            pct = float(((sc < theirs).sum() + 0.5 * (sc == theirs).sum()) / len(sc))
            if a["to_call"] > 0 and not rr_done:
                rr_done = True
                self.rr_sd[0] += 1
                self.rr_sd[1] += pct
            self.bluffs[1] += 1
            if pct < PARAMS["bluff_pct"]:
                self.bluffs[0] += 1

    def floor(self):
        """Likelihood floor for hands outside his betting range; small when he never bluffs."""
        s = PARAMS["bluff_prior_n"]
        b = (PARAMS["bluff_prior"] * s + self.bluffs[0]) / (s + self.bluffs[1])
        lo = PARAMS["rm_floor_min"]
        v = lo + (PARAMS["rm_floor"] - lo) * b / PARAMS["bluff_prior"]
        return min(PARAMS["rm_floor_max"], max(lo, v))

    def pf_rate(self, key, big):
        table = PARAMS["pf_prior_big" if big else "pf_prior_small"]
        hits = self.pf_big if big else self.pf_small
        s = PARAMS["opp_prior_n"]
        return (table[key] * s + hits[key]) / (s + self.pf_opps[key])

    def pf_jam_rate(self, key):
        s = PARAMS["opp_prior_n"]
        return (PARAMS["pf_prior_big"][key] * s + self.pf_allin[key]) / (s + self.pf_opps[key])

    def pf_range(self, key, big, size):
        """Share of hands he raises with at this spot and size."""
        if big:
            return min(1.0, max(0.02, self.pf_rate(key, True)))
        p = self.pf_rate(key, False) + self.pf_rate(key, True)
        ref = PARAMS["pf_size_ref"][key]
        p *= min(1.2, max(0.6, (ref / max(size, 1)) ** 0.5))
        return min(1.0, max(0.03, p))

    def pf_fold_to_raise(self):
        s = PARAMS["opp_prior_n"]
        return (PARAMS["pf_fold_prior"] * s + self.pf_fold[0]) / (s + self.pf_fold[1])

    def pf_fold_to_3bet(self):
        s = PARAMS["opp_prior_n"]
        return (PARAMS["pf_fold_prior"] * s + self.pf_fold3[0]) / (s + self.pf_fold3[1])

    def aggression(self):
        """Postflop bet/raise share of his actions, None until enough are seen."""
        if self.agg[1] < PARAMS["agg_min_n"]:
            return None
        s = PARAMS["opp_prior_n"]
        return (PARAMS["agg_prior"] * s + self.agg[0]) / (s + self.agg[1])

    def fold_prob(self, street, ratio, facing_raise=False):
        """Chance he folds to a bet of this size (fraction of the pot)."""
        b = self.bucket(ratio)
        prior = PARAMS["fold_prior"].get(street, PARAMS["fold_prior"]["river"])[b]
        s = PARAMS["opp_prior_n"]
        if facing_raise:
            # a selective bettor rarely folds the hand he just bet
            prior *= PARAMS["fold_raise_mult"] * self.bet_selectivity()
        # sparse size cells borrow from the other sizes of the same street and kind
        pooled = [0, 0]
        for key, cell in self.fold_c.items():
            if key[0] == street and key[1] == bool(facing_raise):
                pooled[0] += cell[0]
                pooled[1] += cell[1]
        prior = (prior * s + pooled[0]) / (s + pooled[1])
        hit, n = self.fold_c.get((street, bool(facing_raise), b), (0, 0))
        return (prior * s + hit) / (s + n)

    def bet_selectivity(self):
        """Scale 0.2..1 from how often he bets when checked to; rare bets mean strength."""
        s = PARAMS["opp_prior_n"]
        ref = PARAMS["rm_aggr_prior"][0]
        rate = (ref * s + self.bet_chk[0]) / (s + self.bet_chk[1])
        return min(1.0, max(PARAMS["sel_floor"], rate / ref))

    def raise_read(self):
        """Equity to subtract when facing his raise: shown strength of his raises plus how rarely he raises."""
        pen = 0.0
        n, s = self.rr_sd
        if n >= PARAMS["rr_read_min"]:
            k = PARAMS["rr_read_min"]
            est = (PARAMS["rr_read_prior"] * k + s) / (k + n)
            pen = PARAMS["rr_read_gain"] * (est - PARAMS["rr_read_cut"])
        if self.face[1] >= PARAMS["rr_sel_n"]:
            rate = self.face[0] / float(self.face[1])
            if (rate < PARAMS["rr_sel_rate"] and n >= PARAMS["rr_read_min"]
                    and s / n >= PARAMS["rr_read_cut"]):
                pen += PARAMS["rr_sel_pen"] * (PARAMS["rr_sel_rate"] - rate) / PARAMS["rr_sel_rate"]
        return min(PARAMS["rr_read_cap"], max(0.0, pen))

    def reraise_prob(self):
        """Chance he raises when a postflop bet faces him."""
        s = PARAMS["opp_prior_n"]
        return (PARAMS["reraise_prob"] * s + self.face[0]) / (s + self.face[1])

    def static_kind(self):
        """The one action nearly every decision was (fold, call or raise), else None."""
        k = self.kinds
        groups = (("fold", k["fold"]), ("call", k["check"] + k["call"]), ("raise", k["raise"]))
        n = sum(g[1] for g in groups)
        if n < PARAMS["static_min_n"]:
            return None
        name, top = max(groups, key=lambda g: g[1])
        return name if top >= PARAMS["static_share"] * n else None

    def static(self):
        """True once nearly every decision he made was the same action."""
        return self.static_kind() is not None

    def alpha(self):
        """Steepness of his action-versus-strength link, shrunk toward the default."""
        base = PARAMS["rm_alpha"]
        if self.static():
            return 0.0
        n = min(self.sd_agg[0], self.sd_pas[0])
        if n == 0:
            return base
        sep = self.sd_agg[1] / self.sd_agg[0] - self.sd_pas[1] / self.sd_pas[0]
        est = base * min(PARAMS["alpha_cap"], max(0.0, sep / PARAMS["alpha_sep_ref"]))
        s = PARAMS["opp_prior_n"]
        return (base * s + est * n) / (s + n)

    def beta(self):
        """Discard sharpness: a one-in-three match with our keep model means random."""
        base = PARAMS["keep_beta"]
        if self.static():
            return 0.0
        s = PARAMS["opp_prior_n"]
        rate = (PARAMS["keep_prior_rate"] * s + self.keep_hits[0]) / (s + self.keep_hits[1])
        span = PARAMS["keep_prior_rate"] - 1.0 / 3.0
        return base * min(PARAMS["beta_cap"], max(0.0, (rate - 1.0 / 3.0) / span))

    def freq(self, street, depth):
        """Share of his range that makes the depth-th bet or raise on this street."""
        s = PARAMS["opp_prior_n"]
        prior = PARAMS["rm_aggr_prior"]
        if street == "preflop":
            key = min(max(depth, 1) - 1, 3)
            return self.pf_rate(key, False) + self.pf_rate(key, True)
        if depth <= 1:
            return (prior[0] * s + self.bet_chk[0]) / (s + self.bet_chk[1])
        return (prior[1] * s + self.face[0]) / (s + self.face[1])

    def cont(self, street, faced, raised=False):
        """Share of his range that continues against a bet of this size."""
        if street == "preflop":
            return None
        return 1.0 - self.fold_prob(street, faced, raised)

    def range_args(self):
        return {"alpha": self.alpha(), "beta": self.beta(), "freq_fn": self.freq,
                "cont_fn": self.cont, "floor": self.floor()}


class MatchState:
    def __init__(self):
        self.clock = Clock()
        self.stack = 200
        self.net = 0
        self.hands_done = 0
        self.hand = None
        self.opp = OppModel()

    def configure(self, msg):
        self.clock.configure(msg)
        self.stack = max(1, as_int(msg.get("starting_stack"), 200))

    def new_hand(self, msg):
        self.clock.observe(msg)
        seat = msg.get("seat") if msg.get("seat") in ("button", "big_blind") else "button"
        self.hand = HandState(as_int(msg.get("hand_id"), self.clock.hand_id), seat,
                              msg.get("hole_cards") or [])

    def observe(self, req):
        self.clock.observe(req)
        if self.hand is None:
            self.hand = HandState(self.clock.hand_id, "button", req.get("hole_cards") or [])
        self.hand.observe(req)

    def discard_result(self, msg):
        if self.hand is not None:
            self.hand.on_discard(msg)

    def hand_result(self, msg):
        net = as_int(msg.get("net"))
        self.net += net
        self.hands_done += 1
        seat = self.hand.seat if self.hand is not None else "button"
        try:
            self.opp.update(msg, seat, self.stack)
        except Exception as exc:
            log("opp model error", repr(exc))
        self.hand = None


STATE = MatchState()


def fallback_action(req):
    legal = req.get("legal_actions") or []
    if "check" in legal:
        return {"type": "action", "action": "check"}
    pot = as_int(req.get("pot"))
    to_call = as_int(req.get("to_call"))
    if "call" in legal and to_call <= PARAMS["fallback_call_frac"] * pot:
        return {"type": "action", "action": "call"}
    if "fold" in legal:
        return {"type": "action", "action": "fold"}
    if "call" in legal:
        return {"type": "action", "action": "call"}
    return {"type": "action", "action": "check"}


def legalize(action, req):
    """Last check: force the reply into the set of legal actions."""
    legal = req.get("legal_actions") or []
    kind = action.get("action")
    if kind == "raise":
        if "raise" in legal:
            lo = as_int(req.get("min_raise"))
            hi = as_int(req.get("max_raise"), lo)
            amount = as_int(action.get("amount"), lo)
            amount = max(lo, min(hi, amount))
            return {"type": "action", "action": "raise", "amount": amount}
        kind = "call" if as_int(req.get("to_call")) > 0 else "check"
    if kind in legal:
        return {"type": "action", "action": kind}
    return fallback_action(req)


def fallback_discard(req):
    cards = [c for c in (req.get("hole_cards") or []) if isinstance(c, str) and len(c) >= 2]
    if not cards:
        return None
    ranks = [rank_of(c) for c in cards]
    paired = {r for r in ranks if ranks.count(r) > 1}
    pool = [c for c in cards if rank_of(c) not in paired] or cards
    return min(pool, key=rank_of)

# ---- keep model: how a hand of three cards is likely to be trimmed to two

def _build_outs():
    # ranks that would complete a straight, for every rank mask
    outs = [0] * 8192
    for m in range(8192):
        if _SH[m]:
            continue
        n = 0
        for r in range(13):
            if not m >> r & 1 and _SH[m | (1 << r)]:
                n += 1
        outs[m] = n
    return outs


_OUTS = _build_outs()
if HAVE_NP:
    _OUTS_NP = np.array(_OUTS, dtype=np.int64)


def _keep_score_one(kept, flop):
    """Value of keeping two cards on the given flop (scalar form of keep_scores)."""
    val = eval_one(list(kept) + list(flop)) / 1048576.0
    fmask = 0
    fsuit = [0, 0, 0, 0]
    fmax = 0
    for c in flop:
        fmask |= 1 << (c >> 2)
        fsuit[c & 3] += 1
        fmax = max(fmax, c >> 2)
    mask = fmask
    for c in kept:
        mask |= 1 << (c >> 2)
    if not _SH[mask]:
        gain = _OUTS[mask] - _OUTS[fmask]
        if gain >= 2:
            val += PARAMS["kd_oesd"]
        elif gain == 1:
            val += PARAMS["kd_gutshot"]
    for s in range(4):
        ks = sum(1 for c in kept if c & 3 == s)
        tot = ks + fsuit[s]
        if tot == 4 and ks >= 1:
            val += PARAMS["kd_flush_draw"]
            if any(c & 3 == s and c >> 2 == 12 for c in kept):
                val += PARAMS["kd_nut_flush_draw"]
        elif tot == 3 and ks >= 1:
            val += PARAMS["kd_backdoor"]
    a, b = kept[0] >> 2, kept[1] >> 2
    val += PARAMS["kd_overcard"] * ((a > fmax) + (b > fmax))
    if a == b:
        val += PARAMS["kd_pocket"] * (1 + a / 12.0)
    if a == 12 or b == 12:
        val += PARAMS["kd_ace"]
    return val


def keep_scores(triples, flop):
    """Row per three-card hand; column i is the value of the hand left after discarding card i."""
    if not HAVE_NP:
        out = []
        for t in triples:
            out.append([_keep_score_one((t[(i + 1) % 3], t[(i + 2) % 3]), flop) for i in range(3)])
        return out
    T = np.asarray(triples, dtype=np.int64).reshape(-1, 3)
    F = np.asarray(flop, dtype=np.int64)
    n = T.shape[0]
    frank = F >> 2
    fsuit = np.bincount(F & 3, minlength=4)
    fmask = int(np.bitwise_or.reduce(np.left_shift(1, frank)))
    fmax = int(frank.max())
    fouts = _OUTS[fmask]
    out = np.empty((n, 3), dtype=np.float64)
    hands = np.empty((n, 5), dtype=np.int64)
    hands[:, 2:] = F
    for i in range(3):
        a = T[:, (i + 1) % 3]
        b = T[:, (i + 2) % 3]
        hands[:, 0] = a
        hands[:, 1] = b
        val = eval_batch(hands) / 1048576.0
        ra = a >> 2
        rb = b >> 2
        sa = a & 3
        sb = b & 3
        mask = np.left_shift(1, ra) | np.left_shift(1, rb) | fmask
        gain = _OUTS_NP[mask] - fouts
        no_straight = (_SH_NP[mask] == 0)
        val = val + no_straight * np.where(gain >= 2, PARAMS["kd_oesd"],
                                           np.where(gain == 1, PARAMS["kd_gutshot"], 0.0))
        for s in range(4):
            ks = (sa == s).astype(np.int64) + (sb == s)
            tot = ks + int(fsuit[s])
            nut = ((ra == 12) & (sa == s)) | ((rb == 12) & (sb == s))
            draw = (tot == 4) & (ks >= 1)
            val = val + draw * (PARAMS["kd_flush_draw"] + PARAMS["kd_nut_flush_draw"] * nut)
            val = val + ((tot == 3) & (ks >= 1)) * PARAMS["kd_backdoor"]
        val = val + PARAMS["kd_overcard"] * ((ra > fmax).astype(np.int64) + (rb > fmax))
        val = val + (ra == rb) * PARAMS["kd_pocket"] * (1 + ra / 12.0)
        val = val + ((ra == 12) | (rb == 12)) * PARAMS["kd_ace"]
        out[:, i] = val
    return out


def keep_probs(scores, beta):
    """Softmax over the three keep options; beta 0 is a random discarder."""
    if not HAVE_NP:
        res = []
        for row in scores:
            top = max(row)
            e = [math.exp(beta * (v - top)) for v in row]
            tot = sum(e)
            res.append([v / tot for v in e])
        return res
    sc = np.asarray(scores, dtype=np.float64)
    z = np.exp(beta * (sc - sc.max(axis=1, keepdims=True)))
    return z / z.sum(axis=1, keepdims=True)


# ---- preflop tables: 1755 suit-isomorphic three-card classes

PF_P = (0.05, 0.10, 0.20, 0.35, 0.50, 0.75)
PF_BLOB = (
    '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'
    'TkZJ1tH32of8z/0bsHIZ7Y8OkT/phnaTXzu4Ckh5eGW0gHarWeaklwhOBJFkimI5KrYmc2zWi9VLsptnR5Jpp2VsrDpnfvKGBs2j'
    'b0UjyTK6NnZQ7TER//UgHf0+GkmV0oCcNdFPM52s37KaZV/KjqTS1Cm2W200C5H1utET4JTR+7Ey/bMp938JYrHWsUiqPPwuOl3W'
    'MZ29O4K3gj7RSLqMmuRuyD2Te3+Nt3Mv5U7MjZSV0/jcl3N/ym1f49oaP+Q+k+tUqerMl/c6R6t0xYw/584hpwqjNeY1RqJETlNd'
    '9SntVBE0zXRmG+FuJqpXMTGcKkS32jvYDn6AWmHG5RqnioKmdaDietB59PXD4BiqbjPYOD6JmmJ27wfi0T/GssbcpYR6Rg0BElAB'
    '1NcPvLc0+lHMB6dKjDJtyObwtvCLgR4CJKQ37XcZC3h13J6Dui+QLJpif8/YwW+SWi9D53CqZNNWW5PtQkWfQ1XdCySXplvGtvIh'
    'srY+rB8HAlXp1WaPioeBtDY/AymgN+zBjCZiGfr1UtwMp0qc7vI6s3cFU4v17VDHTpUiWm2/yeglRsu0zjTlQIqps+fxHHcEOAPR'
    'EZ0qJZTt/YmZ4kLr3Gd+BJKkEV6u2Ob2QJVNMw8gqpQk5nsNYnojeu/tQNLQkA1cSzvVBf26+QxIOT3o3Q4n/Joar582RdZhnBpY'
    'w/rzoXD081QMGSZnp2zN46KMfoPb2yMdJilLjeTNxDm3smwsVwMxTgy+srI4C2U5TBYCsfSeepGNhu5N0zkaByRw/lXd+A/8nNtf'
    'figvA4nSEtWBLxbX0ZMVf4cBEjq5ug3PFf2pCfR8rnJYJuXqDH6RF9H9cp/sCiTb6aIDvoU/TfnyFVkPSA711c/x2mIwvGdtzFSH'
    '5TnXm648F371ohyi9gDJp1tNVf6EmEl75d/yBJC484w5z66Cop4rGZyBwwrhYTezDm5juFX2X1SxM972gGesLM/CF0zUDktQys7k'
    'BXQDlN9uKCmHJZ2v7EzRgHrIBqpA7wQnRV9Z6f7uLoBL6aU7gVPx2dc1NAtuo4oZipniQDtO8hj9CR3VUY8xJ63DBbW2W+EUZtMz'
    'qpLerh14qIMyxSfyPe5YWk6NpcMl1P+9fBI/Ck1fTT4ERIWfUiG7wHbh7BvQQnK4oV/lYjaFr8Pduk62AMfSAuXwmfxD9zR823og'
    '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'
)

_PERMS = list(itertools.permutations(range(4)))


def canon(cards):
    """Canonical form of a set of card ints under suit relabelling."""
    best = None
    for perm in _PERMS:
        t = tuple(sorted((c & ~3) | perm[c & 3] for c in cards))
        if best is None or t < best:
            best = t
    return best


PF_INDEX = {}
PF_COMBOS = []
PF_EQ = []
PF_EQ_TOP = []
PF_PCT = []
PF_READY = False


def _decode_preflop(blob):
    global PF_READY
    if not blob:
        return
    raw = zlib.decompress(base64.b64decode(blob))
    rec = struct.Struct("<4B7H")
    for off in range(0, len(raw), rec.size):
        v = rec.unpack_from(raw, off)
        PF_INDEX[(v[0], v[1], v[2])] = len(PF_COMBOS)
        PF_COMBOS.append(v[3])
        PF_EQ.append(v[4] / 10000.0)
        PF_EQ_TOP.append([x / 10000.0 for x in v[5:]])
    order = sorted(range(len(PF_EQ)), key=PF_EQ.__getitem__)
    total = float(sum(PF_COMBOS))
    pct = [0.0] * len(PF_EQ)
    below = 0
    for i in order:
        pct[i] = (below + PF_COMBOS[i] / 2.0) / total
        below += PF_COMBOS[i]
    PF_PCT.extend(pct)
    PF_READY = len(PF_EQ) == 1755 and below == 22100


_decode_preflop("".join(PF_BLOB) if isinstance(PF_BLOB, tuple) else PF_BLOB)


def class_of(three):
    """Table index of a three-card hand (ints), -1 when the table is unavailable."""
    if not PF_READY:
        return -1
    return PF_INDEX.get(canon(three), -1)


def pf_equity_vs_range(cls, p):
    """Equity of a class against the top fraction p of starting hands (1.0 = random hand)."""
    xs = PF_P + (1.0,)
    ys = PF_EQ_TOP[cls] + [PF_EQ[cls]]
    p = min(1.0, max(0.01, p))
    if p <= xs[0]:
        slope = (ys[1] - ys[0]) / (xs[1] - xs[0])
        return min(1.0, max(0.0, ys[0] + slope * (p - xs[0])))
    for i in range(1, len(xs)):
        if p <= xs[i]:
            t = (p - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return ys[-1]


# ---- discard decision

_RNG = np.random.default_rng() if HAVE_NP else random.Random()


def _kept_pair(T, j):
    # cards left in each row after discarding column j[row]
    rows = np.arange(T.shape[0])
    return T[rows, (j + 1) % 3], T[rows, (j + 2) % 3]


def _flop_sim(my3, flop, live, n, beta, rng):
    """Sampled opponent triples, results for our keeps, and opponent keep scores."""
    idx = np.argsort(rng.random((n, live.shape[0])), axis=1)[:, :5]
    draw = live[idx]
    opp = draw[:, :3]
    board = np.concatenate([np.broadcast_to(np.asarray(flop, dtype=np.int64), (n, 3)),
                            draw[:, 3:5]], axis=1)
    ks = keep_scores(opp, flop)
    if beta is None:
        a, b = _kept_pair(opp, ks.argmax(axis=1))
        oscore = [eval_batch(np.concatenate([a[:, None], b[:, None], board], axis=1))]
        probs = None
    else:
        probs = keep_probs(ks, beta)
        oscore = []
        for j in range(3):
            oscore.append(eval_batch(np.concatenate(
                [opp[:, (j + 1) % 3, None], opp[:, (j + 2) % 3, None], board], axis=1)))
    res = np.empty((n, 3), dtype=np.float64)
    for i in range(3):
        k1, k2 = my3[(i + 1) % 3], my3[(i + 2) % 3]
        mine = eval_batch(np.concatenate(
            [np.full((n, 1), k1, dtype=np.int64), np.full((n, 1), k2, dtype=np.int64), board],
            axis=1))
        if probs is None:
            res[:, i] = (mine > oscore[0]) + 0.5 * (mine == oscore[0])
        else:
            acc = 0.0
            for j in range(3):
                acc = acc + probs[:, j] * ((mine > oscore[j]) + 0.5 * (mine == oscore[j]))
            res[:, i] = acc
    return opp, res, ks


def _discard_batch(my3, flop, live, n, weight_fn, beta, rng):
    """Weighted win+tie mass for each of my three keeps over n sampled runouts."""
    opp, res, _ = _flop_sim(my3, flop, live, n, beta, rng)
    if weight_fn is None:
        w = np.ones(n)
    else:
        w = np.asarray(weight_fn(opp), dtype=np.float64)
    return [float((w * res[:, i]).sum()) for i in range(3)], float(w.sum())


def _discard_plain(my3, flop, live, n, rng):
    # no numpy: scalar loop with the same sampling scheme
    mass = [0.0, 0.0, 0.0]
    for _ in range(n):
        d = rng.sample(live, 5)
        opp, board = d[:3], list(flop) + d[3:]
        ks = keep_scores([opp], flop)[0]
        j = ks.index(max(ks))
        o = eval_one([opp[(j + 1) % 3], opp[(j + 2) % 3]] + board)
        for i in range(3):
            m = eval_one([my3[(i + 1) % 3], my3[(i + 2) % 3]] + board)
            mass[i] += (m > o) + 0.5 * (m == o)
    return mass, float(n)


def _reveal(card, flop):
    # how much discarding this card tells the opponent about the rest of the hand
    r, s = card >> 2, card & 3
    franks = [c >> 2 for c in flop]
    score = 2.0 * (r in franks)
    score += 1.0 * (sum(1 for c in flop if c & 3 == s) >= 2)
    score += 0.5 * sum(1 for x in franks if x != r and abs(x - r) <= 2)
    return score


def discard_equities(my3, flop, n=None, deadline=None, weight_fn=None, beta=None, rng=None):
    """Estimated equity of each keep (index = discarded card) and the samples used."""
    n = PARAMS["discard_samples"] if n is None else n
    dead = set(my3) | set(flop)
    live_list = [c for c in range(52) if c not in dead]
    batch = PARAMS["discard_batch"]
    mass = [0.0, 0.0, 0.0]
    total = 0.0
    used = 0
    if HAVE_NP:
        rng = _RNG if rng is None else rng
        live = np.array(live_list, dtype=np.int64)
    else:
        rng = random.Random() if rng is None or not hasattr(rng, "sample") else rng
        n = max(20, n // 10)
        batch = max(10, batch // 10)
    while used < n:
        m = min(batch, n - used)
        if HAVE_NP:
            part, w = _discard_batch(my3, flop, live, m, weight_fn, beta, rng)
        else:
            part, w = _discard_plain(my3, flop, live_list, m, rng)
        for i in range(3):
            mass[i] += part[i]
        total += w
        used += m
        if deadline is not None and time.perf_counter() >= deadline:
            break
    total = total or 1.0
    return [v / total for v in mass], used


def pick_discard(my3, flop, eq):
    """Index to discard: best equity, near ties go to the card that reveals less."""
    best = max(eq)
    near = [i for i in range(3) if eq[i] >= best - PARAMS["discard_tie"]]
    return min(near, key=lambda i: (_reveal(my3[i], flop), my3[i] >> 2, -eq[i]))


def choose_discard(req, weight_fn=None, beta=None, n=None, rng=None):
    hole = req.get("hole_cards")
    board = req.get("board")
    if not (isinstance(hole, list) and isinstance(board, list) and len(hole) == 3
            and len(board) >= 3 and len(set(hole)) == 3):
        return fallback_discard(req)
    my3 = [parse_card(c) for c in hole]
    flop = [parse_card(c) for c in board[:3]]
    if len(set(my3) | set(flop)) != 6:
        return fallback_discard(req)
    budget = STATE.clock.budget("discard")
    if budget <= 0.0 and n is None:
        ks = keep_scores([my3], flop)[0]
        return hole[max(range(3), key=lambda i: ks[i])]
    deadline = None if n is not None else time.perf_counter() + budget
    eq, _ = discard_equities(my3, flop, n=n, deadline=deadline, weight_fn=weight_fn,
                             beta=beta, rng=rng)
    return hole[pick_discard(my3, flop, eq)]


# ---- opponent range model and equity

_PF_NP = {}


def _pf_np():
    if not _PF_NP:
        triples = np.array(list(itertools.combinations(range(52), 3)), dtype=np.int64)
        ranks = triples & ~3
        suits = triples & 3
        best = np.full(len(triples), 1 << 18, dtype=np.int64)
        for perm in _PERMS:
            cards = np.sort(ranks | np.asarray(perm)[suits], axis=1)
            keys = (cards[:, 0] << 12) | (cards[:, 1] << 6) | cards[:, 2]
            np.minimum(best, keys, out=best)
        indices = np.fromiter(
            (PF_INDEX.get((key >> 12, (key >> 6) & 63, key & 63), -1) for key in best),
            dtype=np.int16, count=len(best),
        )
        lookup = np.full((52, 52, 52), -1, dtype=np.int16)
        for a, b, c in itertools.permutations(range(3)):
            lookup[triples[:, a], triples[:, b], triples[:, c]] = indices
        _PF_NP.update(lookup=lookup, pct=np.array(PF_PCT, dtype=np.float64))
    return _PF_NP


def class_batch(T):
    """Table index for each row of an (N, 3) array of card ints, -1 when unknown."""
    T = np.asarray(T, dtype=np.int64)
    return _pf_np()["lookup"][T[:, 0], T[:, 1], T[:, 2]]


def _sig(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30.0, 30.0)))


def _wpct(x, w=None):
    """Percentile of each value among all values (weighted), ties share the middle."""
    order = np.argsort(x, kind="stable")
    xs = x[order]
    ws = np.ones(len(x)) if w is None else w[order]
    cum = np.concatenate([[0.0], np.cumsum(ws)])
    lo = cum[np.searchsorted(xs, x, side="left")]
    hi = cum[np.searchsorted(xs, x, side="right")]
    total = cum[-1]
    if total <= 0:
        return np.full(len(x), 0.5)
    return (lo + hi) / (2.0 * total)


class RangeModel:
    """Likelihood of an opponent holding a sampled hand given what he did and discarded."""

    def __init__(self, spots=(), opp_discard=None, my_discard=None, alpha=None, beta=None,
                 freq_fn=None, cont_fn=None, floor=None):
        self.spots = list(spots)
        self.opp_discard = opp_discard
        self.my_discard = my_discard
        self.alpha = PARAMS["rm_alpha"] if alpha is None else alpha
        self.beta = PARAMS["keep_beta"] if beta is None else beta
        self.freq_fn = freq_fn
        self.cont_fn = cont_fn
        self.floor = PARAMS["rm_floor"] if floor is None else floor
        self.dead = {c for c in (opp_discard, my_discard) if c is not None}

    @classmethod
    def from_hand(cls, history, hand, stack=200, freq_fn=None, cont_fn=None, alpha=None,
                  beta=None, floor=None):
        parsed = parse_history(history, hand.seat, stack)
        spots = []
        for a in parsed.actions:
            if a["actor"] != "opp" or a["action"] == "fold":
                continue
            base = 1 if a["street"] == "preflop" else 0
            before = a["raise_no"] - base - (1 if a["is_raise"] else 0)
            owed = a["to_call"]
            spots.append({
                "street": a["street"],
                "kind": a["action"],
                "before": max(0, before),
                "faced": owed / max(1, a["pot_before"] - owed),
                "frac": a["frac"],
            })

        # probe F1: a check-raise is at least as strong as a lead, so the check says nothing about weakness
        cr = {sp["street"] for sp in spots if sp["kind"] == "raise" and sp["street"] != "preflop"}
        spots = [sp for sp in spots if not (sp["kind"] == "check" and sp["street"] in cr)]

        def card(x):
            return parse_card(x) if isinstance(x, str) and len(x) == 2 else None

        return cls(spots, card(hand.opp_discard), card(hand.my_discard), alpha=alpha, beta=beta,
                   freq_fn=freq_fn, cont_fn=cont_fn, floor=floor)

    def freq(self, street, depth):
        """Share of his range that makes the depth-th bet or raise on this street."""
        if self.freq_fn is not None:
            v = self.freq_fn(street, depth)
            if v is not None:
                return min(0.95, max(0.02, v))
        prior = PARAMS["rm_aggr_prior"]
        return prior[min(depth, len(prior)) - 1]

    def _lik(self, sp, s):
        a = self.alpha
        street = sp["street"]
        if sp["kind"] == "raise":
            shift = PARAMS["rm_size_shift"] * (min(2.5, max(0.2, sp["frac"])) - 0.66)
            lik = _sig(a * (s - (1.0 - self.freq(street, sp["before"] + 1) + shift)))
        elif sp["kind"] == "check":
            lik = 1.0 - (1.0 - PARAMS["rm_trap"]) * _sig(a * (s - (1.0 - self.freq(street, 1))))
        else:
            cont = None
            if self.cont_fn is not None:
                cont = self.cont_fn(street, sp["faced"], sp["before"] >= 2)
            if cont is None:
                cont = PARAMS["rm_cont_base"] - PARAMS["rm_cont_slope"] * min(3.0, sp["faced"])
            cont = min(0.95, max(0.15, cont))
            stay = _sig(a * (s - (1.0 - cont)))
            punch = _sig(a * (s - (1.0 - self.freq(street, sp["before"] + 1))))
            lik = stay * (1.0 - (1.0 - PARAMS["rm_trap"]) * punch)
        return np.maximum(lik, self.floor)

    def weights(self, T, flop, turn=None, river=None, *, known_keeps=None):
        """Weights and a current-street strength for sampled opponent hands.

        T has three columns (kept pair plus the discard once it is known, or the
        undecided triple on the flop) or two columns (kept pair only)."""
        T = np.asarray(T, dtype=np.int64)
        n = T.shape[0]
        full = T.shape[1] == 3
        cache = {}
        if known_keeps is not None:
            cache["ks"] = known_keeps

        def keeps():
            if "ks" not in cache:
                cache["ks"] = keep_scores(T, flop)
            return cache["ks"]

        def made(board):
            key = len(board)
            if key not in cache:
                B = np.broadcast_to(np.asarray(board, dtype=np.int64), (n, key))
                cache[key] = eval_batch(np.concatenate([T[:, :2], B], axis=1))
            return cache[key]

        board4 = list(flop) + [turn] if turn is not None else None
        board5 = board4 + [river] if board4 is not None and river is not None else None
        w = np.ones(n)
        strengths = {}
        for sp in self.spots:
            street = sp["street"]
            if street in strengths:
                s = strengths[street]
            elif street == "preflop" and full:
                cls = class_batch(T)
                s = np.where(cls >= 0, _pf_np()["pct"][np.maximum(cls, 0)], 0.5)
            elif street == "flop" and full:
                s = _wpct(keeps().max(axis=1))
            elif street == "turn" and board4 is not None:
                s = _wpct(made(board4))
            elif street == "river" and board5 is not None:
                s = _wpct(made(board5))
            else:
                continue
            strengths[street] = s
            w = w * self._lik(sp, s)
        if full and board4 is not None and self.opp_discard is not None:
            w = w * keep_probs(keeps(), self.beta)[:, 2]
        if board5 is not None:
            cur = made(board5)
        elif board4 is not None:
            cur = made(board4)
        elif full:
            cur = keeps().max(axis=1)
        else:
            cur = np.zeros(n)
        return w, cur


class EquityInfo:
    """Per-sample results against a weighted range, with continue-fraction reweighting."""

    def __init__(self, res, w, cur, n, keep=None, keeps=None):
        self.n = n
        self.keep = keep
        self.keeps = keeps
        if HAVE_NP:
            self.res = np.asarray(res, dtype=np.float64)
            self.w = np.asarray(w, dtype=np.float64)
            if self.w.sum() <= 0:
                self.w = np.ones(len(self.res))
            self.s = _wpct(np.asarray(cur, dtype=np.float64), self.w)
            self.e_all = float((self.w * self.res).sum() / self.w.sum())
        else:
            self.res = list(res)
            self.w = list(w)
            order = sorted(range(len(cur)), key=cur.__getitem__)
            self.s = [0.0] * len(cur)
            for rank, i in enumerate(order):
                self.s[i] = (rank + 0.5) / len(cur)
            self.e_all = sum(a * b for a, b in zip(self.w, self.res)) / sum(self.w)

    def e_vs_continue(self, f):
        """Equity against the strongest fraction f of his range (soft cut)."""
        f = min(1.0, max(0.02, f))
        if f >= 0.999:
            return self.e_all
        k = PARAMS["eq_cont_alpha"]
        if HAVE_NP:
            c = self.w * _sig(k * (self.s - (1.0 - f)))
            tot = float(c.sum())
            return float((c * self.res).sum() / tot) if tot > 0 else self.e_all
        c = [a / (1.0 + math.exp(-max(-30.0, min(30.0, k * (s - (1.0 - f))))))
             for a, s in zip(self.w, self.s)]
        tot = sum(c)
        return sum(a * r for a, r in zip(c, self.res)) / tot if tot > 0 else self.e_all


def _finish_flop(R, w, cur, n):
    tot = float(sum(w)) or 1.0
    if HAVE_NP:
        mass = [float((w * R[:, i]).sum()) for i in range(3)]
    else:
        mass = [sum(a * r[i] for a, r in zip(w, R)) for i in range(3)]
    best = max(range(3), key=mass.__getitem__)
    col = R[:, best] if HAVE_NP else [r[best] for r in R]
    return EquityInfo(col, w, cur, n, keep=best, keeps=[m / tot for m in mass])


def _equity_plain(street, mine, board, dead, n):
    # no numpy: uniform range and scalar sampling with one tenth of the samples
    rng = random.Random()
    live = [c for c in range(52) if c not in dead]
    n = max(20, n // 10)
    rows, cur = [], []
    for _ in range(n):
        if street == "flop":
            d = rng.sample(live, 5)
            ks = keep_scores([d[:3]], board)[0]
            j = ks.index(max(ks))
            b = list(board) + d[3:]
            o = eval_one([d[(j + 1) % 3], d[(j + 2) % 3]] + b)
            rows.append([(m > o) + 0.5 * (m == o) for m in
                         (eval_one([mine[(i + 1) % 3], mine[(i + 2) % 3]] + b) for i in range(3))])
            cur.append(max(ks))
        else:
            d = rng.sample(live, 3 if street == "turn" else 2)
            b = list(board) + d[2:]
            o = eval_one(d[:2] + b)
            m = eval_one(list(mine) + b)
            rows.append([(m > o) + 0.5 * (m == o)])
            cur.append(eval_one(d[:2] + list(board)))
    w = [1.0] * n
    if street == "flop":
        return _finish_flop(rows, w, cur, n)
    return EquityInfo([r[0] for r in rows], w, cur, n)


def equity_flop(my3, flop, rm=None, budget=None, n=None, rng=None):
    """Best keep on the flop against the weighted range; keep is the index to discard."""
    rm = rm or RangeModel()
    n = PARAMS["eq_flop_samples"] if n is None else n
    if not HAVE_NP:
        return _equity_plain("flop", my3, flop, set(my3) | set(flop), n)
    rng = _RNG if rng is None else rng
    dead = set(my3) | set(flop)
    live = np.array([c for c in range(52) if c not in dead], dtype=np.int64)
    deadline = None if budget is None else time.perf_counter() + budget
    opps, ress, keeps = [], [], []
    used = 0
    while used < n:
        m = min(PARAMS["eq_batch"], n - used)
        opp, res, ks = _flop_sim(my3, flop, live, m, rm.beta, rng)
        opps.append(opp)
        ress.append(res)
        keeps.append(ks)
        used += m
        if deadline is not None and used >= PARAMS["eq_min_samples"] \
                and time.perf_counter() >= deadline:
            break
    O = np.concatenate(opps)
    R = np.concatenate(ress)
    w, cur = rm.weights(O, flop, known_keeps=np.concatenate(keeps))
    return _finish_flop(R, w, cur, used)


def _pair_table(my2, board, rm):
    dead = set(my2) | set(board) | rm.dead
    live = np.array([c for c in range(52) if c not in dead], dtype=np.int64)
    i, j = np.triu_indices(len(live), 1)
    pair = np.stack([live[i], live[j]], axis=1)
    if rm.opp_discard is not None:
        pair = np.concatenate([pair, np.full((len(pair), 1), rm.opp_discard, dtype=np.int64)],
                              axis=1)
    return live, i, j, pair


def _rows(cards, n):
    return np.broadcast_to(np.asarray(list(cards), dtype=np.int64), (n, len(cards)))


def equity_turn(my2, board4, rm=None, budget=None, epochs=None, rng=None):
    """Equity on the turn: every opponent pair once per epoch, each with a fresh river."""
    rm = rm or RangeModel()
    if not HAVE_NP:
        return _equity_plain("turn", my2, board4, set(my2) | set(board4) | rm.dead,
                             PARAMS["eq_flop_samples"])
    rng = _RNG if rng is None else rng
    epochs = PARAMS["eq_turn_epochs"] if epochs is None else epochs
    live, i, j, T = _pair_table(my2, board4, rm)
    p = len(T)
    w, cur = rm.weights(T, board4[:3], turn=board4[3])
    mine_by_river = eval_batch(np.concatenate([
        _rows(list(my2) + list(board4), len(live)), live[:, None],
    ], axis=1))
    opp_base = np.concatenate([T[:, :2], _rows(board4, p)], axis=1)
    deadline = None if budget is None else time.perf_counter() + budget
    total = np.zeros(p)
    done = 0
    while done < epochs:
        r = rng.integers(0, len(live) - 2, size=p)
        idx = r + (r >= i)
        idx = idx + (idx >= j)
        river = live[idx][:, None]
        mine = mine_by_river[idx]
        opp = eval_batch(np.concatenate([opp_base, river], axis=1))
        total += (mine > opp) + 0.5 * (mine == opp)
        done += 1
        if deadline is not None and time.perf_counter() >= deadline:
            break
    return EquityInfo(total / done, w, cur, p * done)


def equity_river(my2, board5, rm=None):
    """Exact equity on the river over every live opponent pair."""
    rm = rm or RangeModel()
    if not HAVE_NP:
        return _equity_plain("river", my2, board5, set(my2) | set(board5) | rm.dead,
                             PARAMS["eq_flop_samples"])
    live, i, j, T = _pair_table(my2, board5, rm)
    p = len(T)
    w, cur = rm.weights(T, board5[:3], turn=board5[3], river=board5[4])
    mine = eval_one(list(my2) + list(board5))
    res = (mine > cur) + 0.5 * (mine == cur)
    return EquityInfo(res, w, cur, p)


# ---- betting policy

def _act(kind, amount=None):
    out = {"type": "action", "action": kind}
    if amount is not None:
        out["amount"] = int(amount)
    return out


def _raise_range(req):
    lo = as_int(req.get("min_raise"))
    hi = as_int(req.get("max_raise"), lo)
    return lo, max(lo, hi)


def decide_preflop(req, hole, opp=None, rng=random):
    """Table-driven preflop play from the embedded class equities."""
    opp = opp or STATE.opp
    legal = req.get("legal_actions") or []
    mb = as_int(req.get("my_bet"))
    ob = as_int(req.get("opp_bet"))
    c = as_int(req.get("to_call"))
    pot = max(1, as_int(req.get("pot"), mb + ob))
    my_stack = as_int(req.get("my_stack"))
    opp_stack = as_int(req.get("opp_stack"))
    seat = STATE.hand.seat if STATE.hand is not None else "button"
    start = STATE.stack
    can_raise = "raise" in legal
    cls = class_of(hole)
    pct = PF_PCT[cls] if cls >= 0 else 0.5
    parsed = parse_history(req.get("history"), seat, start)
    k = parsed.raises - 1
    if ob > 2 and k < 1:
        k = 1

    if c <= 0:
        if can_raise and pct >= PARAMS["pf_iso_cut"]:
            return _act("raise", PARAMS["pf_iso_size"])
        return _act("check")

    if k == 0:
        # Key 1 covers the big blind facing our first raise, after the open.
        jam_rate = opp.pf_jam_rate(1)
        if seat == "button" and jam_rate >= PARAMS["pf_shove_rate"]:
            jam = max(0, start - PARAMS["pf_open_size"])
            need = jam / float(2 * start) + PARAMS["pf_shove_margin"]
            eq = pf_equity_vs_range(cls, jam_rate) if cls >= 0 else 0.4
            if eq <= need:
                return _act("fold")
        steal = PARAMS["pf_steal_slope"] * max(0.0, opp.pf_fold_to_raise() - PARAMS["pf_steal_base"])
        if can_raise and pct >= max(0.0, PARAMS["pf_open_cut"] - steal):
            loose = opp.pf_fold_to_raise() < PARAMS["pf_loose_fold"]
            return _act("raise", PARAMS["pf_open_size_loose" if loose else "pf_open_size"])
        if pct >= PARAMS["pf_limp_cut"]:
            return _act("call")
        return _act("fold")

    prev_raises = k - 1
    key = 4 if (prev_raises == 0 and seat == "button") else min(prev_raises, 3)
    big = ob >= PARAMS["pf_big_frac"] * start or opp_stack <= 0
    p = opp.pf_range(key, big, ob)
    eq = pf_equity_vs_range(cls, p) if cls >= 0 else 0.4
    odds = c / float(pot + c)
    if big:
        margin = PARAMS["pf_big_margin"]
        if p >= 0.9 or opp.static_kind() == "raise":
            margin = PARAMS["pf_shove_margin"]
    else:
        margin = PARAMS["pf_call_margin"] + (PARAMS["pf_oop_margin"] if seat == "big_blind" else 0.0)

    if can_raise:
        if big and eq >= PARAMS["pf_jam_eq"]:
            return _act("raise", as_int(req.get("max_raise")))
        if not big and eq >= PARAMS["pf_value_eq"] and rng.random() < PARAMS["pf_value_freq"]:
            if prev_raises == 0:
                return _act("raise", ob * PARAMS["pf_raise_mult"])
            return _act("raise", as_int(req.get("max_raise")))
        has_ace = any((x >> 2) == 12 for x in hole)
        if (not big and prev_raises == 0 and has_ace and eq < odds + margin + 0.05
                and opp.pf_fold_to_raise() > PARAMS["pf_bluff_fold"]
                and rng.random() < PARAMS["pf_bluff_freq"]):
            return _act("raise", ob * PARAMS["pf_raise_mult"])
    if eq > odds + margin:
        return _act("call")
    return _act("fold")


def _realization(req, street, ip):
    c = as_int(req.get("to_call"))
    if street == "river" or as_int(req.get("my_stack")) <= c or as_int(req.get("opp_stack")) <= 0:
        return 1.0
    return PARAMS["real_ip" if ip else "real_oop"].get(street, 1.0)


def _dry_board(board):
    ranks = sorted(c >> 2 for c in board[:3])
    suits = [c & 3 for c in board[:3]]
    return len(set(suits)) == 3 and len(set(ranks)) == 3 and ranks[-1] - ranks[0] >= 5


def _call_tax(street, P, c, opp):
    """Equity discount on big flop and turn calls: such raises are stronger than the range model says."""
    if street == "river" or c < PARAMS["big_call_min"] or c < PARAMS["big_call_odds"] * (P + c):
        return 0.0
    agg = opp.aggression()
    return PARAMS["big_call_tax"] if agg is None or agg <= PARAMS["mdf_aggr"] else 0.0


def _beats_all(hole, board, ties_ok):
    """True when our two cards beat (or, with ties_ok, at least tie) every two-card holding."""
    dead = set(hole) | set(board)
    live = [x for x in range(52) if x not in dead]
    mine = eval_one(list(hole) + list(board))
    if HAVE_NP:
        lv = np.array(live, dtype=np.int64)
        i, j = np.triu_indices(len(lv), 1)
        rows = np.concatenate([np.stack([lv[i], lv[j]], axis=1), _rows(board, len(i))], axis=1)
        best = int(eval_batch(rows).max())
    else:
        best = max(eval_one([live[a], live[b]] + list(board))
                   for a in range(len(live)) for b in range(a + 1, len(live)))
    return mine >= best if ties_ok else mine > best


def _nut_cap(pen, street, hole, board):
    """Raise-read penalty after the cannot-lose check: none on the river, small on the turn."""
    if pen <= 0.0 or hole is None or len(hole) != 2:
        return pen
    if street == "river" and len(board) == 5 and _beats_all(hole, board, True):
        return 0.0
    if street == "turn" and len(board) == 4 and _beats_all(hole, board, False):
        return min(pen, PARAMS["rr_nut_turn_cap"])
    return pen


def decide(req, info, opp=None, rng=random):
    """Pick the highest-EV action (chips relative to folding now) from an equity summary."""
    opp = opp or STATE.opp
    legal = req.get("legal_actions") or []
    street = req.get("street")
    P = max(1, as_int(req.get("pot")))
    c = as_int(req.get("to_call"))
    mb = as_int(req.get("my_bet"))
    ob = as_int(req.get("opp_bet"))
    my_stack = as_int(req.get("my_stack"))
    opp_stack = as_int(req.get("opp_stack"))
    left = as_int(req.get("raises_left"), 1)
    hand = STATE.hand
    ip = hand is None or hand.seat == "button"
    R = _realization(req, street, ip)
    e = info.e_all
    pen = 0.0
    if street != "preflop" and c > 0 and mb > 0 and hasattr(opp, "raise_read"):
        pen = opp.raise_read()  # he raised over our bet: discount by how strong his raises show
        if pen > 0.0 and hand is not None and street in ("turn", "river"):
            try:
                pen = _nut_cap(pen, street, [parse_card(x) for x in hand.hole],
                               [parse_card(x) for x in (req.get("board") or [])])
            except Exception as exc:
                log("nut cap error", repr(exc))
    e -= pen

    evs = {}
    if "fold" in legal:
        evs[("fold", 0)] = 0.0
    if "check" in legal:
        evs[("check", 0)] = R * e * P
    if "call" in legal:
        evs[("call", 0)] = R * (e - _call_tax(street, P, c, opp)) * (P + c) - c
    raise_to = []
    if "raise" in legal:
        lo, hi = _raise_range(req)
        targets = set()
        for frac in PARAMS["bet_sizes"]:
            targets.add(max(lo, min(hi, int(round(ob + frac * (P + c))))))
        if min(my_stack, opp_stack + c) <= PARAMS["max_shove_spr"] * (P + c):
            targets.add(hi)
        for to in sorted(targets):
            a = to - mb
            if a <= 0:
                continue
            d = max(0, min(to - ob, opp_stack))
            ratio = a / float(P)
            f = opp.fold_prob(street, ratio, c > 0)
            e_c = info.e_vs_continue(1.0 - f) - pen
            q = P + a + d
            show = R * e_c * q - a
            rr = opp.reraise_prob() if (left > 1 and opp_stack - d > 0 and my_stack - a > 0) \
                else 0.0
            if rr > 0:
                y = min(my_stack - a, opp_stack - d, q)
                e_rr = info.e_vs_continue(max(0.02, (1.0 - f) * PARAMS["rr_range"])) - pen
                hit = max(-a, R * e_rr * (q + 2 * y) - a - y)
                show = (1.0 - rr) * show + rr * hit
            evs[("raise", to)] = f * P + (1.0 - f) * show
            raise_to.append(to)

    if not evs:
        return fallback_action(req)
    best = max(evs.values())
    eps = PARAMS["mix_eps"] * P
    pick = max(evs, key=evs.get)

    allin_to = max(raise_to) if raise_to else None
    spr = min(my_stack, opp_stack + c) / float(P)
    passive = [v for k_, v in evs.items() if k_[0] in ("check", "call", "fold")]
    if (allin_to is not None and spr < PARAMS["spr_shove"] and evs[("raise", allin_to)] > 0
            and evs[("raise", allin_to)] >= max(passive or [0.0]) - 0.05 * P):
        pick = ("raise", allin_to)
    elif pick[0] != "fold":
        near = [k_ for k_, v in evs.items() if k_[0] != "fold" and v >= best - eps]
        if len(near) > 1:
            ws = [math.exp(-(best - evs[k_]) / (0.5 * eps)) for k_ in near]
            r = rng.random() * sum(ws)
            for k_, w in zip(near, ws):
                r -= w
                if r <= 0:
                    pick = k_
                    break

    if c > 0 and "call" in legal and opp.static_kind() == "raise":
        # he raises whatever he holds, so only our equity against a random hand matters
        need = c / float(P + c) + PARAMS["static_margin"]
        keep_raise = (pick[0] == "raise" and evs[pick] > 0
                      and evs[pick] >= evs.get(("call", 0), 0.0))
        if not keep_raise:
            pick = ("call", 0) if e > need else ("fold", 0)
    elif pick[0] == "fold" and "call" in legal:
        agg = opp.aggression()
        if agg is not None and agg > PARAMS["mdf_aggr"] \
                and e > c / float(P + c) - PARAMS["mdf_slack"]:
            pick = ("call", 0)

    if pick[0] != "raise" and street == "flop" and c == 0 and raise_to and hand is not None:
        pick = _cbet_floor(req, evs, raise_to, pick, opp, P, rng)

    return _act(pick[0], pick[1] if pick[0] == "raise" else None)


def _cbet_floor(req, evs, raise_to, pick, opp, P, rng):
    """Keep a minimum continuation-bet rate as the preflop aggressor on dry flops."""
    board = [parse_card(x) for x in (req.get("board") or [])[:3]]
    if len(board) < 3 or not _dry_board(board):
        return pick
    parsed = parse_history(req.get("history"), STATE.hand.seat, STATE.stack)
    last = [a for a in parsed.actions if a["street"] == "preflop" and a["is_raise"]]
    if not last or last[-1]["actor"] != "me":
        return pick
    to = min(raise_to)
    ratio = (to - as_int(req.get("my_bet"))) / float(P)
    if opp.fold_prob("flop", ratio, False) < PARAMS["cbet_fold_min"]:
        return pick
    if evs[("raise", to)] < -PARAMS["cbet_tol"] * P:
        return pick
    if rng.random() < PARAMS["cbet_freq"]:
        return ("raise", to)
    return pick


def street_equity(req, hand, hole, board):
    """Equity summary for the current street against the weighted opponent range."""
    street = req["street"]
    rm = RangeModel.from_hand(req.get("history"), hand, STATE.stack, **STATE.opp.range_args())
    budget = STATE.clock.budget(street)
    if street == "flop":
        if len(hole) != 3:
            raise ValueError("flop needs three cards")
        if budget <= 0.0:
            return equity_flop(hole, board, rm, n=200)
        return equity_flop(hole, board, rm, budget=budget)
    if len(hole) != 2:
        raise ValueError("turn and river need two cards")
    if street == "turn":
        if budget <= 0.0:
            return equity_turn(hole, board, rm, epochs=1)
        return equity_turn(hole, board, rm, budget=budget)
    return equity_river(hole, board, rm)


def choose_action(req):
    hand = STATE.hand
    street = req.get("street")
    if hand is None or street not in STREETS:
        return fallback_action(req)
    if len(hand.hole) != (3 if street in ("preflop", "flop") else 2):
        return fallback_action(req)
    hole = [parse_card(x) for x in hand.hole]
    if street == "preflop":
        return decide_preflop(req, hole)
    board = [parse_card(x) for x in (req.get("board") or [])]
    if len(board) != {"flop": 3, "turn": 4, "river": 5}[street]:
        return fallback_action(req)
    if len(set(hole) | set(board)) != len(hole) + len(board):
        return fallback_action(req)
    info = street_equity(req, hand, hole, board)
    return decide(req, info)


def handle_action(req):
    try:
        if STATE.clock.time_left_ms <= LAST_REPLY_RESERVE_MS:
            reply = fallback_action(req)
        else:
            reply = legalize(choose_action(req), req)
    except Exception as exc:
        log("action error", repr(exc))
        try:
            reply = legalize(fallback_action(req), req)
        except Exception:
            reply = {"type": "action", "action": "check"}
    send(reply)


def handle_discard(req):
    cards = req.get("hole_cards")
    cards = [c for c in cards if isinstance(c, str)] if isinstance(cards, list) else []
    if len(cards) < 2 and STATE.hand is not None:
        # a damaged request still has to be answered from the hand we were dealt
        cards = [c for c in STATE.hand.hole if isinstance(c, str)]
        req = dict(req, hole_cards=cards)
    try:
        if STATE.clock.time_left_ms <= LAST_REPLY_RESERVE_MS:
            card = fallback_discard(req)
        else:
            card = choose_discard(req)
    except Exception as exc:
        log("discard error", repr(exc))
        card = None
    if card not in cards:
        try:
            card = fallback_discard(req)
        except Exception:
            card = cards[0] if cards else None
    if card is None:
        # a reply that may be rejected still beats waiting out the timeout
        card = "2c"
    send({"type": "discard", "card": card})


def observe(method, msg):
    # state tracking must never block a reply
    try:
        method(msg)
    except Exception as exc:
        log("state error", repr(exc))


def dispatch(msg):
    """Handle one message; return False when the match is over."""
    kind = msg.get("type")
    if kind == "action_request":
        observe(STATE.observe, msg)
        handle_action(msg)
    elif kind == "discard_request":
        observe(STATE.observe, msg)
        handle_discard(msg)
    elif kind == "init":
        observe(STATE.configure, msg)
    elif kind == "new_hand":
        observe(STATE.new_hand, msg)
    elif kind == "discard_result":
        observe(STATE.discard_result, msg)
    elif kind == "hand_result":
        observe(STATE.hand_result, msg)
    elif kind == "match_end":
        return False
    return True


def main():
    gc.collect()
    gc.freeze()
    try:
        sys.stdin.reconfigure(errors="replace")
    except Exception:
        pass
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except (ValueError, RecursionError):
            continue
        if not isinstance(msg, dict):
            continue
        try:
            if not dispatch(msg):
                break
        except Exception as exc:
            log("handler error", repr(exc))


# ---------------- sweep style layer: candidate34 lead layer (shipped in candidate34; identical logic to the tested c32_donk) ----------------
import random as _rs
_SW_RNG = _rs.Random(6221057)
_SW_BASE_DECIDE = decide
_SW_BASE_PF = decide_preflop


def _sw_pot_to(req, frac):
    lo, hi = _raise_range(req)
    P = max(1, as_int(req.get("pot")))
    c = as_int(req.get("to_call"))
    ob = as_int(req.get("opp_bet"))
    return max(lo, min(hi, int(round(ob + frac * (P + c)))))


def decide(req, info, opp=None, rng=random):
    out = _SW_BASE_DECIDE(req, info, opp, rng)
    legal = req.get("legal_actions") or []
    if req.get("street") in ("flop", "turn") and as_int(req.get("to_call")) == 0 and "raise" in legal             and _SW_RNG.random() < 0.7:
        return _act("raise", _sw_pot_to(req, 0.6))
    return out


if __name__ == "__main__":
    main()
