#!/usr/bin/env python3
"""Synergy'26 Pokerbots final bot (Discard Hold'em). Lineage: nova (written from the problem statement alone)
-> fable5_b_fast (team champion until 15 Nov) -> this bot: flop/turn bets 0.33/0.5 pot, 450 pre-discard samples.

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
P = dict(PROFILES[PROFILE])
P.update(sz=(0.33, 0.5), n=450)                 # final push: smaller bet-size menu
PRE_TRUTH = True       # preflop also uses flop-chosen keeps (fable5_b)
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
    x = np.bitwise_or.reduce(np.int64(1) << (s * 16 + r), axis=-1)   # suit su's rank mask = bits 16su..16su+12
    for su in range(4):                              # OR, not sum: masked-out rows may repeat a card
        v = np.maximum(v, FLUSH[(x >> (16 * su)) & 8191])
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
        self.rr3 = Rate(0.12, 6)                    # preflop: he raises when facing our raise, before raising himself
        self.rr4 = Rate(0.25, 6)                    # preflop: he raises again when facing our re-raise of his raise
        self.stab = {st: Rate(0.45, 6) for st in ("flop", "turn", "river")}   # he bets after we check first on st
        self.frb = {st: Rate(0.25, 8) for st in ("flop", "turn", "river")}   # he bet/raised this street, then faced our sized raise: fold rate
        self.fja = Rate(0.10, 8)                                              # same, but our raise was all-in (pooled over postflop streets)
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
            if street == "preflop":                 # sharper range for a low-frequency raiser (no-op at v = vmax)
                tau = float(np.clip(0.3 * v, 0.01, 0.06))
                lik = b + (1 - b) / (1.0 + np.exp(-np.clip((s - thr) / tau, -30, 30)))
            else:
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
    h = np.empty((6, n, 2 + full.shape[1]), dtype=np.int64)    # rows 0-2 our keeps, 3-5 his
    for k, (i, j) in enumerate(KEEP):
        h[k, :, 0], h[k, :, 1] = me[i], me[j]
        h[3 + k, :, 0], h[3 + k, :, 1] = opp3[:, i], opp3[:, j]
    h[:, :, 2:] = full
    e = ev(h)
    myv, ovs = np.ascontiguousarray(e[:3].T), np.ascontiguousarray(e[3:].T)
    ov = ovs.max(1)
    ar = np.arange(n)
    mk = None
    if board or PRE_TRUTH:
        try:                                        # keeps are chosen on the flop: his always, ours too preflop
            kq = kq5(h[3:, :, :5] if board else h[:, :, :5])
            ov = ovs[ar, kq[-3:].argmax(0)]
            mk = None if board else kq[:3].argmax(0)
        except Exception:
            ov, mk = ovs.max(1), None
    win_k = (myv > ov[:, None]) + 0.5 * (myv == ov[:, None])
    mb = myv.max(1)
    if board:
        mb = myv[:, int(np.argmax(win_k.mean(0)))]  # the caller re-picks with range weights
    elif mk is not None:
        mb = myv[ar, mk]
    win = (mb > ov) + 0.5 * (mb == ov)
    S = {"preflop": (pct(prescore(opp3)), 1.0)}
    if board:
        if len(board) == 3:                         # h[3:, :, :5] = his pair + the flop
            S["flop"] = (pct(ev5(h[3:, :, :5]).max(0)), 1.0)
        else:
            fl = np.tile(np.array(board, dtype=np.int64), (n, 1))
            S["flop"] = (pct(np.stack([ev(np.concatenate([opp3[:, [i, j]], fl], 1)) for i, j in KEEP], 1).max(1)), 1.0)
    return win, win_k, S


def keep_quality(a, b, flop):
    return kq5(np.stack([a, b] + [np.full_like(a, c) for c in flop], -1))


_K5 = (KEYS[:, None] // POW5 % 5).sum(1) == 5     # 5-card rank multisets only (smaller search table)
KEYS5, VALS5 = KEYS[_K5], VALS[_K5]
SUIT8 = 8 ** np.arange(4, dtype=np.int64)          # suit counts in base 8 -> largest count
SCMAX = np.array([max((k >> (3 * i)) & 7 for i in range(4)) for k in range(4096)], dtype=np.int64)


def _t5():
    r = np.indices((13,) * 5).reshape(5, -1).T                  # every ordered 5-tuple of ranks, idx order
    m = np.zeros(len(r), dtype=np.int64)
    for k in range(5):
        m |= np.int64(1) << r[:, k]
    v = VALS5[np.minimum(np.searchsorted(KEYS5, POW5[r].sum(-1)), len(KEYS5) - 1)]
    f = np.maximum(v, FLUSH[m])
    su = np.indices((4,) * 5).reshape(5, -1).T
    return (v, f, v // C5 + (v % C5) / C5, f // C5 + (f % C5) / C5, 0.6 * SD[m],
            SCMAX[SUIT8[su].sum(-1)])


T_V, T_VF, T_A, T_F, T_S, SC5 = _t5()


def _i5(h):
    r, s = h >> 2, h & 3
    return (r[..., 0] * 28561 + r[..., 1] * 2197 + r[..., 2] * 169 + r[..., 3] * 13 + r[..., 4],
            SC5[s[..., 0] * 256 + s[..., 1] * 64 + s[..., 2] * 16 + s[..., 3] * 4 + s[..., 4]])


def kq5(h):
    """keep_quality for an (..., 5) array of 5 distinct cards: 2 kept cards + 3 flop cards per row.
    Same as ev() on 5 cards: a flush needs all five suited, and then FLUSH[rank mask] is its value."""
    i, sc = _i5(h)
    return np.where(sc == 5, T_F[i], T_A[i]) + 0.9 * (sc >= 4) + T_S[i]


def ev5(h):
    """ev() on an (..., 5) array of 5 distinct cards."""
    i, sc = _i5(h)
    return np.where(sc == 5, T_VF[i], T_V[i])


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
        if seat == "big_blind" and street != "preflop":
            # out of position: he bets 0.6 pot after our check with his learned stab rate q, best hands first;
            # if he checks back we keep our share against his checking range, if he bets we call only when it pays
            q = float(np.clip(opp.stab[street](), 0.05, 0.95))
            v = min(q * (1 - opp.bluff()), P["vmax"])
            eb = (v * cont(1 - v)[1] + (q - v) * e) / q
            Rz = 1.0 if street == "river" else 0.9
            bev = Rz * pot * max(0.0, e - q * eb) + q * pot * max(0.0, 2.2 * eb - 0.6)
        elif P.get("induce") and street != "preflop" and not closes:
            # checking lets him bet: he bets a 0.6-pot bet with rate q, his best hands first and the rest as bluffs
            q = float(np.clip(opp.bet[street](), 0.05, 0.95))
            v = min(q * (1 - opp.bluff()), 0.42)
            eb = (v * cont(1 - v)[1] + (q - v) * e) / q
            bev += P["induce"] * q * 0.6 * pot * max(0.0, 2 * eb - 1)
        chk = bev                                   # check value, used by the out-of-position bluff gate
    else:
        best, bev = {"type": "action", "action": "fold"}, 0.0
        m = 0.0 if street == "river" else P["margin"] * pot + (0.25 if street == "preflop" else 0.0)
        cev = e * pot - (1 - e) * c - m
        if "call" in legal and cev > bev:
            best, bev = {"type": "action", "action": "call"}, cev
    if "raise" in legal:
        lo, hi = req["min_raise"], req["max_raise"]
        sizes = (P.get("pfs", 1.0),) if street == "preflop" else (P["szr"] if street == "river" else P["sz"])
        for f in sizes:
            R = int(min(hi, max(lo, req["opp_bet"] + round(f * (pot + c)))))
            if R >= 0.7 * hi:
                R = hi
            add, oadd = R - req["my_bet"], R - req["opp_bet"]
            if rr:
                ff = float(np.clip(opp.rrf() * (0.65 + 0.55 * min(f, 2.0)), 0.03, 0.92))
            elif street != "preflop" and c > 0:
                if R >= hi:                         # all-in: no size scaling
                    ff = float(np.clip(opp.fja(), 0.02, 0.92))
                else:
                    ff = float(np.clip(opp.frb[street]() * (0.65 + 0.55 * min(f, 2.0)), 0.03, 0.92))
            else:
                ff = opp.foldfrac(street, f)
            fa0, wc0 = cont(ff)
            bluff = wc0 < 0.5 and e < 0.45
            rb = 0.0                                # raise-back cost, only for out-of-position bluff leads
            if bluff and c == 0 and seat == "big_blind" and street != "preflop":
                # out of position lead: skip with probability 1 - p, p grows with the EV margin over checking
                fa0, wc0 = cont(ff * P["bluff_k"])
                # he may raise instead of calling (learned raise rate facing a bet): then we fold and lose the lead
                rb = min(float(np.clip(opp.rai[street](), 0.0, 0.9)), 1 - fa0) * wc0 * (pot + oadd + add)
                rev_b = fa0 * pot + (1 - fa0) * (wc0 * (pot + oadd) - (1 - wc0) * add) - rb
                boost = 0.0 if R >= hi else 2.0 * max(0.0, rev_b - chk) / pot
                if random.random() >= min(1.0, P["bluff_p"] + boost):
                    continue
            elif bluff:
                if random.random() > P["bluff_p"]:
                    continue
                fa0, wc0 = cont(ff * P["bluff_k"])
            rev = fa0 * pot + (1 - fa0) * (wc0 * (pot + oadd) - (1 - wc0) * add) - rb
            if street == "preflop" and R < hi and req.get("raises_left", 0) - 1 > 0 and fa0 < 0.999:
                pr = float(np.clip((opp.rr4 if rr else opp.rr3)(), 0.02, 0.9)) * (1 - fa0)
                ka = int(np.searchsorted(cw, fa0 * W + 1e-9 * W, side="right"))        # first hand that does not fold
                kb = max(ka, int(np.searchsorted(cw, (1 - pr) * W)))                   # first hand that re-raises
                wa, na = (cw[ka - 1], cwin[ka - 1]) if ka > 0 else (0.0, 0.0)
                wb, nb = (cw[kb - 1], cwin[kb - 1]) if kb > 0 else (0.0, 0.0)
                pa, pt = float(wb - wa) / W, float(W - wb) / W                         # he calls / he re-raises
                ec = float(nb - na) / float(wb - wa) if wb - wa > 1e-9 else wc0
                et = float(cwin[-1] - nb) / float(W - wb) if W - wb > 1e-9 else ec
                c4 = min(hi, R + pot + add + oadd) - R                                 # his pot-size re-raise costs us c4 more
                rev = (fa0 * pot + pa * (ec * (pot + oadd) - (1 - ec) * add)
                       + pt * max(-add, et * (pot + oadd + c4) - (1 - et) * (add + c4) - 0.05 * (pot + add + oadd + c4)))
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
        # time safety: bank seen, cost per hand / worst reply cost per mode (ms), last time_left values
        self.bank, self.hc, self.rc = 0.0, [25.0, 8.0], [60.0, 20.0]
        self.ptl = self.htl = None
        self.plv = self.hlv = self.lowhits = 0
        self.fresh, self.low = True, False

    @staticmethod
    def keep_idx(win_k, w):
        if w is not None and len(w) == len(win_k) and w.sum() > 0 and w.sum() ** 2 / (w * w).sum() >= 80:
            return int(np.argmax((w[:, None] * win_k).sum(0)))
        return int(np.argmax(win_k.mean(0)))

    def level(self, req):
        tl = req.get("time_left_ms", 30000)
        R = max(1, self.total - self.hand_id + 1)
        per = tl / R
        lv0 = 0 if per > 40 else (1 if per > 12 else 2)      # fable5_b's rule; never made more expensive below
        try:
            lv = lv0
            self.bank = max(self.bank, tl)
            if self.fresh:                                   # first request of a hand: the previous hand's total cost
                if self.htl is not None and self.hlv < 2:
                    d = min(max(0.0, self.htl - tl), 3.0 * self.hc[self.hlv] + 20.0)
                    self.hc[self.hlv] += 0.1 * (d - self.hc[self.hlv])
                self.htl = tl
            elif self.ptl is not None and self.plv < 2:      # cost of our previous reply in this hand
                self.rc[self.plv] = max(self.ptl - tl, 0.9 * self.rc[self.plv])
            spare = tl - 0.15 * self.bank                    # 15% of the bank is never planned for
            if spare <= 0:
                lv = 2
            else:
                ph = spare / R
                if lv == 0 and (1.25 * self.hc[0] > ph or 3.0 * self.rc[0] > spare):
                    lv = 1
                if lv == 1 and (1.25 * self.hc[1] > ph or 3.0 * self.rc[1] > spare):
                    lv = 2
            if self.fresh:
                self.hlv, self.fresh = lv, False
                for k in range(lv):                          # skipped modes: let the estimate fade so they are retried
                    self.hc[k] *= 0.98
            self.ptl, self.plv, self.low = tl, lv, lv == 2
            if lv != lv0:
                self.lowhits += 1
            return lv
        except Exception:
            return lv0

    def new_hand(self, m):
        self.seat, self.h3, self.h2 = m["seat"], [cid(c) for c in m["hole_cards"]], None
        self.my_dis = self.opp_dis = None
        self.cache = {}
        self.hand_id = m.get("hand_id", self.hand_id + 1)
        self.jam = set()
        self.wk = None
        self.fresh = True

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
            win, win_k, S = self.pre(board, lv)
            w = range_weights(acts, S, self.opp, len(win))
            if board:
                try:
                    self.wk = w
                    win = win_k[:, self.keep_idx(win_k, w)]
                except Exception:
                    pass
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
        out = choose(req, win, w, s, self.opp, street, self.seat, rr)
        try:
            if (out.get("action") == "raise" and street != "preflop" and req["to_call"] > 0
                    and out["amount"] >= req["max_raise"]):
                self.jam.add(street)
        except Exception:
            pass
        return out

    def discard(self, req):
        self.h3 = [cid(c) for c in req["hole_cards"]]
        board = [cid(c) for c in req["board"]]
        lv = self.level(req)
        if lv == 2:
            return min(req["hole_cards"], key=lambda c: RANKS.index(c[0]))
        _, win_k, _ = self.pre(board, lv)
        try:
            k = self.keep_idx(win_k, getattr(self, "wk", None))
        except Exception:
            k = int(np.argmax(win_k.mean(0)))
        gone = ({0, 1, 2} - set(KEEP[k])).pop()
        return req["hole_cards"][gone]

    def learn(self, m):
        hist = m.get("history", [])
        opp_raised_pf = False
        obet, nopp, seen = set(), {}, {}            # streets he bet/raised on so far; his action count per street
        jam = ()
        try:
            jam = getattr(self, "jam", ()) or ()
            for h in hist:
                if h.get("actor") == "opp":
                    nopp[h.get("street")] = nopp.get(h.get("street"), 0) + 1
        except Exception:
            pass
        for street, actor, act, facing, fr, last in walk(hist, self.seat):
            if actor != "opp":
                continue
            if street == "preflop":
                if facing and opp_raised_pf:
                    self.opp.rrf.add(act == "fold")
                if facing:
                    try:
                        (self.opp.rr4 if opp_raised_pf else self.opp.rr3).add(act == "raise")
                    except Exception:
                        pass
                if act == "raise":
                    opp_raised_pf = True
            ab = jx = False
            try:
                if street != "preflop":
                    seen[street] = seen.get(street, 0) + 1
                    ab = street in obet                 # he bet or raised earlier on this street
                    jx = street in jam and seen[street] == nopp.get(street, -1)   # his last action on it
                    if act == "raise":
                        obet.add(street)
            except Exception:
                ab = jx = False
            if facing:
                done = False
                if ab:
                    try:
                        (self.opp.fja if jx else self.opp.frb[street]).add(act == "fold")
                        done = True
                    except Exception:
                        pass
                if not done:
                    self.opp.fold[street].add(act == "fold")
                    self.opp.foldb[(street, self.opp.bucket(last))].add(act == "fold")
                self.opp.rai[street].add(act == "raise")
            else:
                self.opp.bet[street].add(act == "raise")
                if street != "preflop" and self.seat == "big_blind":
                    try:
                        self.opp.stab[street].add(act == "raise")
                    except Exception:
                        pass
        oc = m.get("opp_hole_cards")
        if m.get("result") == "showdown" and oc and len(oc) == 2 and len(m.get("board", [])) == 5 and self.h2 and not getattr(self, "low", False):
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
                try:
                    bot.bank = float(m.get("time_bank_ms") or 0.0)
                except Exception:
                    pass
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
