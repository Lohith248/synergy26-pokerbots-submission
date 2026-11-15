"""Rebuild the submitted bot.py from the previous team champion and check it byte for byte.

usage: python reproduce/build.py        (run from the repository root)

The final bot is the previous champion `fable5_b_fast` with exactly three text changes:
  1. the header comment,
  2. the flop/turn bet-size menu 0.4/0.8 pot -> 0.33/0.5 pot, and 600 -> 450 pre-discard samples,
  3. the preflop raise size reads the profile (value unchanged: 1.0 pot).
"""
import hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "base_fable5_b_fast.py")
FINAL = os.path.join(HERE, "..", "bot.py")
BASE_SHA = "93847682573617103bea8bf6d54861544cd1b2942aaf3b2582ad70293e555143"
FINAL_SHA = "7bfe5231831fe29e7585fb3fa7608799d82e03653204b44d1da6554b0cef3da8"

src = open(BASE, encoding="utf-8", newline="").read()
assert hashlib.sha256(src.encode("utf-8")).hexdigest() == BASE_SHA, "base file changed"
EDITS = [
    ('"""nova: Discard Hold\'em bot written from the problem statement alone (test opponent, never submitted).\n',
     '"""Synergy\'26 Pokerbots final bot (Discard Hold\'em). Lineage: nova (written from the problem statement alone)\n'
     '-> fable5_b_fast (team champion until 15 Nov) -> this bot: flop/turn bets 0.33/0.5 pot, 450 pre-discard samples.\n'),
    ('P = PROFILES[PROFILE]\n',
     'P = dict(PROFILES[PROFILE])\nP.update(sz=(0.33, 0.5), n=450)                 # final push: smaller bet-size menu\n'),
    ('sizes = (1.0,) if street == "preflop" else',
     'sizes = (P.get("pfs", 1.0),) if street == "preflop" else'),
]
out = src
for old, new in EDITS:
    assert out.count(old) == 1, old[:50]
    out = out.replace(old, new)
sha = hashlib.sha256(out.encode("utf-8")).hexdigest()
have = hashlib.sha256(open(FINAL, "rb").read()).hexdigest()
print("rebuilt sha256  ", sha)
print("bot.py sha256   ", have)
print("MATCH" if sha == have == FINAL_SHA else "MISMATCH")
sys.exit(0 if sha == have == FINAL_SHA else 1)
