"""Card encoding is rank * 4 + suit, ranks 2..A and suits s,h,d,c."""

from collections.abc import Sequence
from itertools import combinations, permutations

RANKS = "23456789TJQKA"
SUITS = "shdc"
PERMS = tuple(permutations(range(4)))


def card(text: str) -> int:
    return RANKS.index(text[0]) * 4 + SUITS.index(text[1])


def canonical(cards: Sequence[int]) -> str:
    return min(
        ".".join(str(x) for x in sorted((c // 4) * 4 + p[c % 4] for c in cards))
        for p in PERMS
    )


def score(cards: Sequence[int]) -> tuple[int, ...]:
    """Best five-card rank from five to seven distinct cards, higher wins."""
    counts = [0] * 15
    suits: list[list[int]] = [[], [], [], []]
    for c in cards:
        r = c // 4 + 2
        counts[r] += 1
        suits[c % 4].append(r)

    def straight(ranks: Sequence[int]) -> int:
        mask = 0
        for r in ranks:
            mask |= 1 << r
        if mask & (1 << 14):
            mask |= 1 << 1
        for high in range(14, 4, -1):
            if mask & (31 << (high - 4)) == 31 << (high - 4):
                return high
        return 0

    for suited in suits:
        if len(suited) >= 5:
            sf = straight(suited)
            if sf:
                return (8, sf)
    quads = [r for r in range(14, 1, -1) if counts[r] == 4]
    if quads:
        return (
            7,
            quads[0],
            max(r for r in range(2, 15) if counts[r] and r != quads[0]),
        )
    trips = [r for r in range(14, 1, -1) if counts[r] >= 3]
    pairs = [r for r in range(14, 1, -1) if counts[r] >= 2]
    if trips:
        other = [r for r in pairs if r != trips[0]]
        if other:
            return (6, trips[0], other[0])
    for suited in suits:
        if len(suited) >= 5:
            return (5, *sorted(suited, reverse=True)[:5])
    st = straight([r for r in range(2, 15) if counts[r]])
    if st:
        return (4, st)
    if trips:
        return (
            3,
            trips[0],
            *[r for r in range(14, 1, -1) if counts[r] and r != trips[0]][:2],
        )
    if len(pairs) >= 2:
        return (
            2,
            pairs[0],
            pairs[1],
            max(r for r in range(2, 15) if counts[r] and r not in pairs[:2]),
        )
    if pairs:
        return (
            1,
            pairs[0],
            *[r for r in range(14, 1, -1) if counts[r] and r != pairs[0]][:3],
        )
    return (0, *[r for r in range(14, 1, -1) if counts[r]][:5])


def keep_score(pair: Sequence[int], flop: Sequence[int]) -> float:
    """Flop-only made strength plus simple straight and flush draw features."""
    cs = tuple(pair) + tuple(flop)
    made = score(cs)
    value: float = made[0] * 2.0 + sum(
        v / (15 ** (i + 1)) for i, v in enumerate(made[1:])
    )
    suits = [sum(c % 4 == s for c in cs) for s in range(4)]
    value += 0.50 if max(suits) == 4 else 0.0
    ranks = {c // 4 + 2 for c in cs}
    if 14 in ranks:
        ranks.add(1)
    draws = max(sum(r in ranks for r in range(low, low + 5)) for low in range(1, 11))
    return value + (0.28 if draws == 4 else 0.0)


def discard_index(triple: Sequence[int], flop: Sequence[int]) -> int:
    return max(
        range(3),
        key=lambda i: keep_score([c for j, c in enumerate(triple) if j != i], flop),
    )


def straight_flush_discard(triple: Sequence[int], flop: Sequence[int]) -> int | None:
    """Certify a made flop straight flush that dominates every keep on every runout."""
    if len(flop) != 3 or any(c % 4 != flop[0] % 4 for c in flop):
        return None
    suit = flop[0] % 4
    if sum(c % 4 == suit for c in triple) < 2:
        return None
    board = tuple(flop)
    keeps = [tuple(c for j, c in enumerate(triple) if j != i) for i in range(3)]
    made = [score(pair + board) for pair in keeps]
    chosen = max(range(3), key=lambda i: made[i])
    if made[chosen][0] != 8:
        return None
    known = set(triple) | set(flop)
    remaining = [c for c in range(suit, 52, 4) if c not in known]
    for count in range(3):
        for extension in combinations(remaining, count):
            candidate = score(keeps[chosen] + board + extension)
            if any(
                score(pair + board + extension) > candidate
                for i, pair in enumerate(keeps)
                if i != chosen
            ):
                return None
    return chosen
