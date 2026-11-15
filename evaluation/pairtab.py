"""Paired comparison of league rows against a baseline row on the same (opponent, seed, stage).
Usage: python pairtab.py BASE results1.jsonl [results2.jsonl ...] [--groups groups.json] [--min-n 8] [--cols a,b,c]
Prints per row: paired matches, wins row vs base, chips/hand difference with its standard error and t value.
groups.json maps group name -> list of opponent aliases; with it, a line per group is printed as well.
Rows flagged forfeit or error are dropped and counted per row."""
import json, sys, math, collections

args = sys.argv[1:]
groups, min_n, only = None, 8, None
if "--groups" in args:
    i = args.index("--groups"); groups = json.load(open(args[i + 1])); del args[i:i + 2]
if "--min-n" in args:
    i = args.index("--min-n"); min_n = int(args[i + 1]); del args[i:i + 2]
if "--cols" in args:
    i = args.index("--cols"); only = set(args[i + 1].split(",")); del args[i:i + 2]
base, files = args[0], args[1:]
rows = [json.loads(l) for f in files for l in open(f) if l.strip()]
flag = collections.Counter(r["a"] for r in rows if r.get("forfeit") or r.get("error"))
note = collections.Counter()
tmax = collections.defaultdict(float)
D = {}
for r in rows:
    if r.get("forfeit") or r.get("error"):
        continue
    if only and r["b"] not in only:
        continue
    D[(r["a"], r["b"], r["seed"], r["stage"])] = (r["net_a"] / r["hands"], r["points_a"])
    note[r["a"]] += r.get("notices_a", 0)
    tmax[r["a"]] = max(tmax[r["a"]], r.get("time_a", 0.0))
names = sorted({k[0] for k in D})


def stat(a, cols=None):
    d, wa, wb = [], 0.0, 0.0
    for (x, b, s, st), (c, p) in D.items():
        if x != a or (cols is not None and b not in cols):
            continue
        o = D.get((base, b, s, st))
        if o is None:
            continue
        d.append(c - o[0]); wa += p; wb += o[1]
    n = len(d)
    if n < 2:
        return None
    m = sum(d) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1))
    se = sd / math.sqrt(n)
    return n, wa, wb, m, se, m / se if se > 0 else 0.0


out = []
for a in names:
    if a == base:
        continue
    s = stat(a)
    if s and s[0] >= min_n:
        out.append((s[3], a, s))
bn = sum(1 for k in D if k[0] == base)
print(f"base {base}: {bn} clean matches, wins {sum(v[1] for k, v in D.items() if k[0] == base):.1f}, "
      f"mean {sum(v[0] for k, v in D.items() if k[0] == base) / max(1, bn):+.3f} c/h, max time {tmax[base]:.1f}s, flagged {flag[base]}")
print(f"{'row':14s} {'n':>5s} {'wins':>7s} {'base':>7s} {'dW':>6s} {'d c/h':>8s} {'se':>6s} {'t':>6s}  flag notices maxT")
for m, a, (n, wa, wb, mm, se, t) in sorted(out, reverse=True):
    print(f"{a:14s} {n:5d} {wa:7.1f} {wb:7.1f} {wa - wb:+6.1f} {mm:+8.3f} {se:6.3f} {t:+6.2f}  {flag[a]:3d} {note[a]:3d} {tmax[a]:6.1f}")
    if groups:
        for g, cols in groups.items():
            s = stat(a, set(cols))
            if s:
                print(f"   {g:11s} {s[0]:5d} {s[1]:7.1f} {s[2]:7.1f} {s[1] - s[2]:+6.1f} {s[3]:+8.3f} {s[4]:6.3f} {s[5]:+6.2f}")
