"""Final evidence table. python fintab.py BASE label=glob [label=glob ...] [--cols file]
Per row and run: paired matches, match wins row vs base (same deals), discordant pairs (row-only wins / base-only wins) with a
two-sided sign-test p, chips/hand difference with t, paired mean clock ratio, max clock (s, both legs), forfeits/errors, notices."""
import json, sys, glob, math, collections
args = sys.argv[1:]
only = None
if "--cols" in args:
    i = args.index("--cols"); only = {l.strip() for l in open(args[i + 1]) if l.strip() and not l.startswith("#")}; del args[i:i + 2]
base = args[0]

def signp(a, b):
    n, k = a + b, min(a, b)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n)

def load(pat):
    D, flag, note = {}, collections.Counter(), collections.Counter()
    for f in glob.glob(pat):
        for l in open(f):
            if not l.strip():
                continue
            r = json.loads(l)
            if only and r["b"] not in only:
                continue
            if r.get("forfeit") or r.get("error"):
                flag[r["a"]] += 1; continue
            note[r["a"]] += r.get("notices_a", 0)
            D[(r["a"], r["b"], r["seed"], r["stage"])] = (r["net_a"] / r["hands"], r["points_a"], r.get("time_a", 0.0))
    return D, flag, note

def stat(D, a):
    d, wa, wb, up, dn, ta, tb, mx = [], 0.0, 0.0, 0, 0, 0.0, 0.0, 0.0
    for (x, b, s, st), (c, p, t) in D.items():
        if x != a:
            continue
        o = D.get((base, b, s, st))
        if o is None:
            continue
        d.append(c - o[0]); wa += p; wb += o[1]; ta += t; tb += o[2]; mx = max(mx, t)
        up += p > o[1]; dn += p < o[1]
    n = len(d)
    if n < 2:
        return None
    m = sum(d) / n
    se = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1) / n)
    return n, wa, wb, up, dn, m, m / se if se else 0.0, ta / tb if tb else 0.0, mx

pool = {}
hdr = f"{'run':6s} {'row':10s} {'n':>5s} {'wins':>7s} {'base':>7s} {'dW':>6s} {'+/-':>9s} {'p':>6s} {'d c/h':>7s} {'t':>6s} {'clock':>6s} {'maxT':>6s} flag note"
print(hdr)
runs = []
for a in args[1:]:
    label, pat = a.split("=", 1)
    D, flag, note = load(pat); runs.append((label, D, flag, note))
    rows = sorted({k[0] for k in D} - {base})
    bm = max([v[2] for k, v in D.items() if k[0] == base] or [0])
    print(f"{label:6s} {base:10s} {sum(1 for k in D if k[0]==base):5d} {sum(v[1] for k,v in D.items() if k[0]==base):7.1f} {'':7s} {'':6s} {'':9s} {'':6s} {'':7s} {'':6s} {'1.000':>6s} {bm:6.1f} {flag[base]:4d} {note[base]:4d}")
    for r in rows:
        s = stat(D, r)
        if not s:
            continue
        n, wa, wb, up, dn, m, t, cr, mx = s
        print(f"{label:6s} {r:10s} {n:5d} {wa:7.1f} {wb:7.1f} {wa-wb:+6.1f} {up:4d}/{dn:<4d} {signp(up,dn):6.3f} {m:+7.3f} {t:+6.2f} {cr:6.3f} {mx:6.1f} {flag[r]:4d} {note[r]:4d}")
