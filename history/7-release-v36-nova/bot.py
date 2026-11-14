#!/usr/bin/env python3
"""nova: Discard Hold'em bot written from the problem statement alone (test opponent, never submitted).

Design: every decision is an expected-value comparison against a weighted opponent range.
  - before the discard: Monte Carlo over opponent 3-card hands and the rest of the board
  - after the discard: every opponent 2-card hand is enumerated (turn: times every river card)
  - the range is weighted by what his actions and his exposed discard say, using rates measured on him
"""
import sys, json, math, random, itertools
import numpy as np

PROFILE = "t7"
PROFILES = {
    #        samples  bet sizes (pot fractions)                bluff freq/scale      call margin  priors                      learn
    "base":   dict(n=600, sz=(0.4, 0.8), szr=(0.4, 0.8, 1.4), bluff_p=0.75, bluff_k=1.0, margin=0.03, trap0=0.25, bluff0=0.25, fold0=0.40, adapt=1.0),
    "tight":  dict(n=600, sz=(0.4, 0.8), szr=(0.4, 0.8, 1.2), bluff_p=0.50, bluff_k=0.7, margin=0.07, trap0=0.35, bluff0=0.18, fold0=0.35, adapt=1.0),
    "agg":    dict(n=600, sz=(0.6, 1.0), szr=(0.6, 1.0, 1.8), bluff_p=0.95, bluff_k=1.2, margin=0.00, trap0=0.20, bluff0=0.33, fold0=0.50, adapt=1.0),
    "tight2": dict(n=600, sz=(0.4, 0.8), szr=(0.4, 0.8, 1.2), bluff_p=0.50, bluff_k=0.7, margin=0.07, trap0=0.35, bluff0=0.18, fold0=0.35, adapt=1.0, vmax=0.42),
    # tight2 plus one idea each, then all three: recent-form blend, fold rate learned per bet size, checking to induce bets
    "t3": dict(n=600, sz=(0.4, 0.8), szr=(0.4, 0.8, 1.2), bluff_p=0.50, bluff_k=0.7, margin=0.07, trap0=0.35, bluff0=0.18, fold0=0.35, adapt=1.0, vmax=0.42, recent=0.5),
    "t4": dict(n=600, sz=(0.4, 0.8), szr=(0.4, 0.8, 1.2), bluff_p=0.50, bluff_k=0.7, margin=0.07, trap0=0.35, bluff0=0.18, fold0=0.35, adapt=1.0, vmax=0.42, sizefold=1),
    "t5": dict(n=600, sz=(0.4, 0.8), szr=(0.4, 0.8, 1.2), bluff_p=0.50, bluff_k=0.7, margin=0.07, trap0=0.35, bluff0=0.18, fold0=0.35, adapt=1.0, vmax=0.42, induce=1.0),
    "t6": dict(n=600, sz=(0.4, 0.8), szr=(0.4, 0.8, 1.2), bluff_p=0.50, bluff_k=0.7, margin=0.07, trap0=0.35, bluff0=0.18, fold0=0.35, adapt=1.0, vmax=0.42, recent=0.5, sizefold=1, induce=1.0),
    # t6 plus a fold rate learned separately for an opponent who already raised this preflop (his fold to our 3-bet/4-bet)
    "t7": dict(n=600, sz=(0.4, 0.8), szr=(0.4, 0.8, 1.2), bluff_p=0.50, bluff_k=0.7, margin=0.07, trap0=0.35, bluff0=0.18, fold0=0.35, adapt=1.0, vmax=0.42, recent=0.5, sizefold=1, induce=1.0, rrfold=0.25),
    "static": dict(n=600, sz=(0.4, 0.8), szr=(0.4, 0.8, 1.4), bluff_p=0.75, bluff_k=1.0, margin=0.03, trap0=0.25, bluff0=0.25, fold0=0.40, adapt=0.0),
}
P = PROFILES[PROFILE]
np.seterr(all="ignore")
RANKS, SUITS = "23456789TJQKA", "shdc"
RNG = np.random.default_rng()


def cid(c):
    return RANKS.index(c[0]) * 4 + SUITS.index(c[1])


# ---------------------------------------------------------------- evaluator
# value = category * 13^5 + tie-break ranks in base 13; works on 5, 6 or 7 cards, any leading shape
C5 = 13 ** 5
POW5 = 5 ** np.arange(13, dtype=np.int64)
IDX = np.arange(13)


def _straight_top(m):
    for top in range(12, 3, -1):
        if (m >> (top - 4)) & 31 == 31:
            return top
    return 3 if m & 0x100F == 0x100F else -1


STR = np.array([_straight_top(m) for m in range(8192)], dtype=np.int64)


def _flush_val(m):
    bits = [r for r in range(12, -1, -1) if m >> r & 1]
    if len(bits) < 5:
        return 0
    if STR[m] >= 0:
        return 8 * C5 + int(STR[m]) * 13 ** 4
    return 5 * C5 + sum(r * 13 ** (4 - i) for i, r in enumerate(bits[:5]))


FLUSH = np.array([_flush_val(m) for m in range(8192)], dtype=np.int64)
# 1 when four ranks of some straight window are present (a straight draw or better)
SD = np.array([int(any(bin(m & w).count("1") >= 4 for w in [31 << i for i in range(9)] + [0x100F]))
               for m in range(8192)], dtype=np.int64)


def _enc(cat, *rs):
    v = cat * C5
    for i, x in enumerate(rs):
        v = v + x * 13 ** (4 - i)
    return v


def _build():
    rows = []
    for k in (5, 6, 7):
        a = np.array(list(itertools.combinations_with_replacement(range(13), k)), dtype=np.int64)
        cnt = np.stack([(a == r).sum(1) for r in range(13)], 1)
        rows.append(cnt[cnt.max(1) <= 4])
    C = np.concatenate(rows)
    M = len(C)
    present = C > 0
    st = STR[(present * (1 << IDX)).sum(1)]
    order = np.argsort(-(C * 16 + IDX), axis=1, kind="stable")[:, :5]      # ranks by (count, rank), high first
    c = np.take_along_axis(C, order, 1)
    r = np.where(c > 0, order, 0)

    def maxother(*cols):
        ok = present.copy()
        for k in cols:
            ok[np.arange(M), order[:, k]] = False
        return (ok * IDX).max(1)

    c0, c1 = c[:, 0], c[:, 1]
    v = _enc(0, r[:, 0], r[:, 1], r[:, 2], r[:, 3], r[:, 4])
    v = np.where(c0 == 2, _enc(1, r[:, 0], r[:, 1], r[:, 2], r[:, 3]), v)
    v = np.where((c0 == 2) & (c1 == 2), _enc(2, r[:, 0], r[:, 1], maxother(0, 1)), v)
    v = np.where(c0 == 3, _enc(3, r[:, 0], r[:, 1], r[:, 2]), v)
    v = np.where(st >= 0, np.maximum(v, _enc(4, st)), v)
    v = np.where((c0 == 3) & (c1 >= 2), _enc(6, r[:, 0], r[:, 1]), v)
    v = np.where(c0 == 4, _enc(7, r[:, 0], maxother(0)), v)
    key = C @ POW5
    o = np.argsort(key)
    return key[o], v[o]


KEYS, VALS = _build()


def ev(cards):
    r, s = cards >> 2, cards & 3
    v = VALS[np.minimum(np.searchsorted(KEYS, POW5[r].sum(-1)), len(KEYS) - 1)]
    bit = 1 << r
    for su in range(4):                              # OR, not sum: masked-out rows may repeat a card
        v = np.maximum(v, FLUSH[np.bitwise_or.reduce(np.where(s == su, bit, 0), axis=-1)])
    return v


def pct(x):
    n = len(x)
    out = np.empty(n)
    out[np.argsort(x, kind="stable")] = np.arange(n) / max(1, n - 1)
    return out


def g(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x / 0.06, -30, 30)))


# ---------------------------------------------------------------- opponent rates
class Rate:
    def __init__(self, p0, n0):
        self.p0, self.n0, self.k, self.n, self.e = p0, n0, 0.0, 0.0, p0

    def add(self, hit):
        self.n += 1
        self.k += 1 if hit else 0
        self.e = 0.88 * self.e + 0.12 * (1.0 if hit else 0.0)      # recent form, about the last 8 observations

    def __call__(self):
        a = P["adapt"]
        base = (self.p0 * self.n0 + a * self.k) / (self.n0 + a * self.n)
        r = P.get("recent", 0.0)
        return base if r == 0 or self.n < 10 else (1 - r) * base + r * self.e


class Opp:
    def __init__(self):
        post = ("flop", "turn", "river")
        self.fold = {s: Rate(P["fold0"], 8) for s in post}
        self.fold["preflop"] = Rate(0.30, 8)
        self.bet = {s: Rate(0.45, 6) for s in post}
        self.bet["preflop"] = Rate(0.60, 6)
        self.rai = {s: Rate(0.12, 8) for s in post + ("preflop",)}
        self.bluff = Rate(P["bluff0"], 8)
        self.trap = Rate(P["trap0"], 8)
        self.rrf = Rate(P.get("rrfold", 0.25), 6)                   # preflop: folds after he already raised this hand
        # fold rate per street and bet-size bucket (small, medium, large), each starting from the size formula
        self.foldb = {(s, b): Rate(float(np.clip(self.fold[s].p0 * (0.65 + 0.55 * m), 0.03, 0.92)), 6)
                      for s in self.fold for b, m in enumerate((0.4, 0.8, 1.4))}

    @staticmethod
    def bucket(f):
        return 0 if f < 0.55 else (1 if f < 1.1 else 2)

    def foldfrac(self, street, f):
        if P.get("sizefold"):
            return float(np.clip(self.foldb[(street, self.bucket(f))](), 0.03, 0.92))
        return float(np.clip(self.fold[street]() * (0.65 + 0.55 * min(f, 2.0)), 0.03, 0.92))


def walk(history, seat):
    """(street, actor, action, facing a voluntary bet, raise size as pot fraction, size of the bet faced)."""
    bets = {"me": 1 if seat == "button" else 2, "opp": 2 if seat == "button" else 1}
    done, street, aggr, last = 0, "preflop", None, 0.0
    out = []
    for h in history:
        if h["street"] != street:
            done += bets["me"] + bets["opp"]
            bets = {"me": 0, "opp": 0}
            street, aggr, last = h["street"], None, 0.0
        a = h["actor"]
        o = "opp" if a == "me" else "me"
        fr = 0.0
        if h["action"] == "raise":
            pot = done + bets["me"] + bets["opp"]
            fr = (h["amount"] - bets[o]) / max(1.0, pot + max(0, bets[o] - bets[a]))
        out.append((street, a, h["action"], aggr == o, fr, last))
        if h["action"] == "raise":
            bets[a], aggr, last = h["amount"], a, fr
        elif h["action"] == "call":
            bets[a] = bets[o]
    return out


def range_weights(acts, S, opp, n):
    """Likelihood of each candidate opponent hand given his actions; S maps street -> (strength, exponent)."""
    w = np.ones(n)
    bl, trap = opp.bluff(), opp.trap()
    for street, actor, act, facing, fr, last in acts:
        if actor != "opp" or street not in S:
            continue
        s, ex = S[street]
        if act == "raise":
            q = opp.rai[street]() if facing else opp.bet[street]()
            q = float(np.clip(q * (1.15 - 0.35 * min(fr, 1.5)), 0.05, 0.92))
            v = min(q * (1 - bl), P.get("vmax", 1.0))      # nobody holds a value hand more often than vmax
            thr = 1 - v
            b = min(0.95, (q - v) / thr)
            lik = b + (1 - b) * g(s - thr)
        elif act == "check":
            if street == "preflop":
                continue
            q = float(np.clip(opp.bet[street](), 0.05, 0.92))
            thr = 1 - q * (1 - bl)
            b = min(0.95, q * bl / thr)
            lik = 1 - (b + max(0.0, 1 - trap - b) * g(s - thr))
        elif act == "call":
            if not facing:
                continue
            lik = 0.06 + 0.94 * g(s - opp.foldfrac(street, last))
        else:
            continue
        w = w * np.maximum(lik, 1e-4) ** ex
    return w


# ---------------------------------------------------------------- analyses
KEEP = ((0, 1), (0, 2), (1, 2))


def live_cards(dead):
    d = set(dead)
    return np.array([c for c in range(52) if c not in d], dtype=np.int64)


def prescore(h):
    r, s = h >> 2, h & 3
    best = np.zeros(len(h))
    for i, j in KEEP:
        hi, lo = np.maximum(r[:, i], r[:, j]), np.minimum(r[:, i], r[:, j])
        sc = hi + 0.5 * lo + (hi == lo) * (10 + hi) + (s[:, i] == s[:, j]) * 1.5 + ((hi - lo <= 2) & (hi != lo)) * 1.0
        best = np.maximum(best, sc)
    return best + 0.1 * r.sum(1)


def pre_analysis(my3, board, n):
    """Before the discard. Both sides keep their best pair in hindsight, which is symmetric."""
    live = live_cards(my3 + board)
    need = 5 - len(board)
    d = live[np.argsort(RNG.random((n, len(live))), axis=1)[:, :3 + need]]
    opp3, rest = d[:, :3], d[:, 3:]
    full = np.concatenate([np.tile(np.array(board, dtype=np.int64), (n, 1)), rest], 1) if board else rest
    me = np.array(my3, dtype=np.int64)
    myv = np.stack([ev(np.concatenate([np.tile(me[[i, j]], (n, 1)), full], 1)) for i, j in KEEP], 1)
    ov = np.stack([ev(np.concatenate([opp3[:, [i, j]], full], 1)) for i, j in KEEP], 1).max(1)
    win_k = (myv > ov[:, None]) + 0.5 * (myv == ov[:, None])
    mb = myv.max(1)
    win = (mb > ov) + 0.5 * (mb == ov)
    S = {"preflop": (pct(prescore(opp3)), 1.0)}
    if board:
        fl = np.tile(np.array(board, dtype=np.int64), (n, 1))
        S["flop"] = (pct(np.stack([ev(np.concatenate([opp3[:, [i, j]], fl], 1)) for i, j in KEEP], 1).max(1)), 1.0)
    return win, win_k, S


def keep_quality(a, b, flop):
    h = np.stack([a, b] + [np.full_like(a, c) for c in flop], -1)
    v = ev(h)
    r, s = h >> 2, h & 3
    fd = np.max(np.stack([(s == su).sum(-1) for su in range(4)]), 0) >= 4
    m = np.zeros_like(a)
    for k in range(5):
        m |= 1 << r[..., k]
    return v // C5 + (v % C5) / C5 + 0.9 * fd + 0.6 * SD[m]


def post_analysis(my2, board, my_dis, opp_dis, rivers_cap=None):
    """After the discard: every opponent pair; on the turn also every river card."""
    dead = my2 + board + [c for c in (my_dis, opp_dis) if c is not None]
    live = live_cards(dead)
    i, j = np.triu_indices(len(live), 1)
    pairs = np.stack([live[i], live[j]], 1)
    m = len(pairs)
    me = np.array(my2 + board, dtype=np.int64)
    if len(board) == 5:
        ov = ev(np.concatenate([pairs, np.tile(me[2:], (m, 1))], 1))
        mv = int(ev(me))
        win, s = (mv > ov) + 0.5 * (mv == ov), pct(ov)
    else:
        riv = live if rivers_cap is None else RNG.permutation(live)[:rivers_cap]
        L = len(riv)
        b = np.empty((m, L, 7), dtype=np.int64)
        b[:, :, 0:2] = pairs[:, None, :]
        b[:, :, 2:6] = me[2:]
        b[:, :, 6] = riv[None, :]
        ov = ev(b)
        valid = (riv[None, :] != pairs[:, 0:1]) & (riv[None, :] != pairs[:, 1:2])
        mv = ev(np.concatenate([np.tile(me, (L, 1)), riv[:, None]], 1))
        nv = np.maximum(1, valid.sum(1))
        win = (((mv[None, :] > ov) + 0.5 * (mv[None, :] == ov)) * valid).sum(1) / nv
        rk = np.argsort(np.argsort(np.where(valid, ov, -1), axis=0, kind="stable"), axis=0)
        ninv = (~valid).sum(0)
        s = (((rk - ninv) / np.maximum(1, m - ninv - 1)) * valid).sum(1) / nv
    kw = np.ones(m)
    if opp_dis is not None:
        flop = board[:3]
        a, bb = pairs[:, 0], pairs[:, 1]
        d = np.full_like(a, opp_dis)
        alt = np.maximum(keep_quality(a, d, flop), keep_quality(bb, d, flop))
        kw = np.where(keep_quality(a, bb, flop) >= alt - 0.25, 1.0, 0.25)
    return pairs, win, s, kw


# ---------------------------------------------------------------- decision
def choose(req, win, w, s, opp, street, seat, rr=False):
    pot, c, legal = req["pot"], req["to_call"], req["legal_actions"]
    W = float(w.sum())
    if W <= 0:
        w = np.ones(len(w))
        W = float(len(w))
    e = float((w * win).sum() / W)
    o = np.argsort(s, kind="stable")
    cw, cwin = np.cumsum(w[o]), np.cumsum((w * win)[o])

    def cont(ff):                                   # (fraction that folds, my win rate against the rest)
        k = int(np.searchsorted(cw, ff * W))
        if k >= len(cw):
            return 1.0, 0.5
        fw = cw[k - 1] if k > 0 else 0.0
        return fw / W, float((cwin[-1] - (cwin[k - 1] if k > 0 else 0.0)) / max(1e-9, W - fw))

    closes = street == "river" and (c > 0 or seat == "button")
    if c == 0:
        best, bev = {"type": "action", "action": "check"}, e * pot * (1.0 if closes else 0.9)
        if P.get("induce") and street != "preflop" and not closes:
            # checking lets him bet: he bets a 0.6-pot bet with rate q, his best hands first and the rest as bluffs
            q = float(np.clip(opp.bet[street](), 0.05, 0.95))
            v = min(q * (1 - opp.bluff()), 0.42)
            eb = (v * cont(1 - v)[1] + (q - v) * e) / q
            bev += P["induce"] * q * 0.6 * pot * max(0.0, 2 * eb - 1)
    else:
        best, bev = {"type": "action", "action": "fold"}, 0.0
        m = 0.0 if street == "river" else P["margin"] * pot + (0.25 if street == "preflop" else 0.0)
        cev = e * pot - (1 - e) * c - m
        if "call" in legal and cev > bev:
            best, bev = {"type": "action", "action": "call"}, cev
    if "raise" in legal:
        lo, hi = req["min_raise"], req["max_raise"]
        sizes = (1.0,) if street == "preflop" else (P["szr"] if street == "river" else P["sz"])
        for f in sizes:
            R = int(min(hi, max(lo, req["opp_bet"] + round(f * (pot + c)))))
            if R >= 0.7 * hi:
                R = hi
            add, oadd = R - req["my_bet"], R - req["opp_bet"]
            ff = float(np.clip(opp.rrf() * (0.65 + 0.55 * min(f, 2.0)), 0.03, 0.92)) if rr else opp.foldfrac(street, f)
            fa0, wc0 = cont(ff)
            bluff = wc0 < 0.5 and e < 0.45
            if bluff:
                if random.random() > P["bluff_p"]:
                    continue
                fa0, wc0 = cont(ff * P["bluff_k"])
            rev = fa0 * pot + (1 - fa0) * (wc0 * (pot + oadd) - (1 - wc0) * add)
            if rev > bev + 0.02 * pot:
                best, bev = {"type": "action", "action": "raise", "amount": R}, rev
    return best


class Bot:
    def __init__(self):
        self.opp = Opp()
        self.total = 200
        self.seat, self.h3, self.h2 = "button", [], None
        self.my_dis = self.opp_dis = None
        self.cache = {}
        self.hand_id = 1

    def level(self, req):
        per = req.get("time_left_ms", 30000) / max(1, self.total - self.hand_id + 1)
        return 0 if per > 40 else (1 if per > 12 else 2)

    def new_hand(self, m):
        self.seat, self.h3, self.h2 = m["seat"], [cid(c) for c in m["hole_cards"]], None
        self.my_dis = self.opp_dis = None
        self.cache = {}
        self.hand_id = m.get("hand_id", self.hand_id + 1)

    def pre(self, board, lv):
        k = ("pre", len(board))
        if k not in self.cache:
            self.cache[k] = pre_analysis(self.h3, board, P["n"] if lv == 0 else 200)
        return self.cache[k]

    def act(self, req):
        lv = self.level(req)
        legal = req["legal_actions"]
        street = req["street"]
        if lv == 2:                                  # clock emergency: no simulation
            if "check" in legal:
                return {"type": "action", "action": "check"}
            cheap = req["to_call"] <= 0.15 * req["pot"]
            return {"type": "action", "action": "call" if cheap and "call" in legal else "fold"}
        board = [cid(c) for c in req["board"]]
        acts = walk(req.get("history", []), self.seat)
        if self.h2 is None:
            win, _, S = self.pre(board, lv)
            w = range_weights(acts, S, self.opp, len(win))
            s = S["flop"][0] if "flop" in S else S["preflop"][0]
        else:
            k = ("post", len(board))
            if k not in self.cache:
                self.cache[k] = post_analysis(self.h2, board, self.my_dis, self.opp_dis, None if lv == 0 else 12)
            _, win, s, kw = self.cache[k]
            S = {"preflop": (s, 0.25), "flop": (s, 0.5), "turn": (s, 1.0 if street == "turn" else 0.75), "river": (s, 1.0)}
            w = kw * range_weights(acts, S, self.opp, len(win))
        rr = bool(P.get("rrfold")) and street == "preflop" and any(
            st == "preflop" and a == "opp" and ac == "raise" for st, a, ac, _, _, _ in acts)
        return choose(req, win, w, s, self.opp, street, self.seat, rr)

    def discard(self, req):
        self.h3 = [cid(c) for c in req["hole_cards"]]
        board = [cid(c) for c in req["board"]]
        if self.level(req) == 2:
            return min(req["hole_cards"], key=lambda c: RANKS.index(c[0]))
        _, win_k, _ = self.pre(board, 0)
        k = int(np.argmax(win_k.mean(0)))
        gone = ({0, 1, 2} - set(KEEP[k])).pop()
        return req["hole_cards"][gone]

    def learn(self, m):
        hist = m.get("history", [])
        opp_raised_pf = False
        for street, actor, act, facing, fr, last in walk(hist, self.seat):
            if actor != "opp":
                continue
            if street == "preflop":
                if facing and opp_raised_pf:
                    self.opp.rrf.add(act == "fold")
                if act == "raise":
                    opp_raised_pf = True
            if facing:
                self.opp.fold[street].add(act == "fold")
                self.opp.foldb[(street, self.opp.bucket(last))].add(act == "fold")
                self.opp.rai[street].add(act == "raise")
            else:
                self.opp.bet[street].add(act == "raise")
        oc = m.get("opp_hole_cards")
        if m.get("result") == "showdown" and oc and len(oc) == 2 and len(m.get("board", [])) == 5 and self.h2:
            board = [cid(c) for c in m["board"]]
            pairs, _, s, _ = post_analysis(self.h2, board, self.my_dis, self.opp_dis)
            a, b = sorted(cid(c) for c in oc)
            hit = np.nonzero((pairs[:, 0] == a) & (pairs[:, 1] == b))[0]
            if len(hit):
                sv = float(s[hit[0]])
                river = [(h["actor"], h["action"]) for h in hist if h["street"] == "river"]
                if ("opp", "raise") in river:
                    self.opp.bluff.add(sv < 0.4)
                elif "vmax" in P and any(h["actor"] == "opp" and h["action"] == "raise" and h["street"] == "turn" for h in hist):
                    self.opp.bluff.add(sv < 0.4)
                elif ("opp", "check") in river:
                    self.opp.trap.add(sv > 0.8)


def fallback(req):
    legal = req.get("legal_actions", [])
    if "check" in legal:
        return {"type": "action", "action": "check"}
    if "call" in legal and req.get("to_call", 99) <= 0.25 * req.get("pot", 0):
        return {"type": "action", "action": "call"}
    return {"type": "action", "action": "fold" if "fold" in legal else (legal[0] if legal else "check")}


def main():
    bot = Bot()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except ValueError:
            continue
        t = m.get("type") if isinstance(m, dict) else None
        reply = None
        try:
            if t == "init":
                bot.total = int(m.get("total_hands", 200))
            elif t == "new_hand":
                bot.new_hand(m)
            elif t == "action_request":
                try:
                    reply = bot.act(m)
                    if reply["action"] not in m["legal_actions"]:
                        reply = fallback(m)
                except Exception:
                    reply = fallback(m)
            elif t == "discard_request":
                try:
                    reply = {"type": "discard", "card": bot.discard(m)}
                except Exception:
                    reply = {"type": "discard", "card": min(m["hole_cards"], key=lambda c: RANKS.index(c[0]))}
            elif t == "discard_result":
                bot.h2 = [cid(c) for c in m["hole_cards"]]
                bot.my_dis, bot.opp_dis = cid(m["my_discard"]), cid(m["opp_discard"])
            elif t == "hand_result":
                bot.learn(m)
            elif t == "match_end":
                break
        except Exception:
            pass
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
