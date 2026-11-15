"""Per-opponent paired table: python peropp.py BASE ROW files... -> wins and chips/hand of ROW and BASE on the same (opp, seed)."""
import json, sys, collections
base, row, files = sys.argv[1], sys.argv[2], sys.argv[3:]
D = {}
for f in files:
    for l in open(f):
        if l.strip():
            r = json.loads(l)
            if not (r.get("forfeit") or r.get("error")):
                D[(r["a"], r["b"], r["seed"], r["stage"])] = (r["net_a"] / r["hands"], r["points_a"])
per = collections.defaultdict(list)
for (a, b, s, st), v in D.items():
    if a == row and (base, b, s, st) in D:
        per[b].append((v, D[(base, b, s, st)]))
tw = tb = 0
for b, l in sorted(per.items(), key=lambda kv: sum(x[0][0] - x[1][0] for x in kv[1]) / len(kv[1])):
    n = len(l); wr = sum(x[0][1] for x in l); wb = sum(x[1][1] for x in l); tw += wr; tb += wb
    print("%-16s n=%2d  wins %4.1f vs %4.1f (%+.1f)  c/h %+.2f vs %+.2f (%+.2f)" % (b, n, wr, wb, wr - wb, sum(x[0][0] for x in l) / n, sum(x[1][0] for x in l) / n, sum(x[0][0] - x[1][0] for x in l) / n))
print("total wins", tw, "vs", tb)
