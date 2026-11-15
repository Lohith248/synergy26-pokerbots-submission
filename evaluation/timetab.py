"""Mean / p95 / max time_a of each row vs the base row on the same (opponent, seed, stage). usage: python timetab.py BASE files..."""
import json, sys, collections
base, files = sys.argv[1], sys.argv[2:]
T = {}
for f in files:
    for l in open(f):
        if l.strip():
            r = json.loads(l)
            if r.get("forfeit") or r.get("error"):
                continue
            T[(r["a"], r["b"], r["seed"], r["stage"], f)] = r.get("time_a", 0.0)
rows = collections.defaultdict(list)
for (a, b, s, st, f), t in T.items():
    o = T.get((base, b, s, st, f))
    if o is not None and a != base:
        rows[a].append((t, o))
print(f"{'row':12s} {'n':>5s} {'mean':>6s} {'base':>6s} {'ratio':>6s} {'p95':>6s} {'b95':>6s} {'max':>6s} {'bmax':>6s}")
for a, v in sorted(rows.items(), key=lambda kv: -sum(x for x, _ in kv[1]) / sum(y for _, y in kv[1])):
    x = sorted(t for t, _ in v); y = sorted(o for _, o in v); n = len(v)
    print(f"{a:12s} {n:5d} {sum(x)/n:6.2f} {sum(y)/n:6.2f} {sum(x)/sum(y):6.3f} {x[int(.95*n)]:6.2f} {y[int(.95*n)]:6.2f} {x[-1]:6.2f} {y[-1]:6.2f}")
