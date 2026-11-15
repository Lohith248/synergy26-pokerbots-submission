# REVIEW-FINAL: 5 finalists vs champion (15 Nov 2026)

Champion: `../fable5/fable5_b_fast/bot.py`, SHA256 93847682…3e555143 (checked). Line numbers below are in the finalists (identical across all five).
Scripts: [review_startup.py](review_startup.py), [review_outsiders.py](review_outsiders.py). Logs: `stress/stress_<name>.log`, `stress/outsiders_s2_4242.log`.

## Part A: review (`diff --strip-trailing-cr`)

| bot | change at :28-29 | `sizes` at :428 |
|---|---|---|
| z_s2 | `sz=(0.33,0.5)` | unchanged (`(1.0,)` preflop / `szr` river / `sz`) |
| z_v2 | `sz=(0.4,0.8), szx=(0.33,0.5)` | `szx if c>0 else sz` |
| f_c1 | `sz=(0.4,0.8), szt=(0.33,0.5), szx=(0.33,0.5)` | preflop `pfs` default 1.0; `szx` if c>0; `szt` on turn; else `sz` |
| f_v2b | `sz=(0.4,0.8), szx=(0.25,0.5)` | same expression as f_c1 (no `szt`, so turn uses `sz`) |
| f_n45 | `sz=(0.33,0.5), n=450` | preflop `pfs` default 1.0 (same as before); else unchanged |

| item | z_s2 | z_v2 | f_c1 | f_v2b | f_n45 |
|---|---|---|---|---|---|
| 1 diff only the P lines and `sizes` | PASS (sizes not even touched) | PASS | PASS | PASS | PASS |
| 2 `c`, `street` defined at :428 | PASS: `street` is a parameter of `choose` (:385), `c = req["to_call"]` at :386 is unconditional | = | = | = | = |
| 3 non-empty sizes, int clip | PASS: all tuples have 2 or 3 entries, `pfs` is absent so preflop stays `(1.0,)`. :430 `R = int(min(hi, max(lo, …)))`; :431-432 can only raise R to `hi` | = | = | = | = |
| 4 no new import / print / file write | PASS: imports still only :9-10; stdout only through the protocol write at :723-724 | = | = | = | = |
| 5 P mutated only at :29; key uses | PASS: `P["n"]` only at :544; `sz/szx/szt/pfs` only at :428; `szr` only at :428 | = | = | = | = |

**Item 6: code that assumes the old 0.4/0.8 sizes** (none of it breaks anything, and there is no model of our own sizing)
- `Opp.bucket` :173-174 (`<0.55` → bucket 0, `<1.1` → 1, else 2) and the `foldb` priors :169-170 (seeded for m = 0.4/0.8/1.4). Used by `foldfrac` :176-179 because profile t7 has `sizefold=1`.
  - z_s2 and f_n45 (flop + turn), and f_c1 (turn): 0.33 and 0.5 **both fall in bucket 0**. The model gives both sizes the same fold rate, and that prior was seeded for a 0.4 bet. So 0.33 gets slightly too much fold equity, the 0.5 bet looks equally good, and the model loses its old ability to tell a small bet from a big one. Bucket 1 for flop/turn stops getting updates (:645 buckets by the size actually bet, `last`). This is a mild, self-correcting bias, not a bug.
  - z_v2, f_c1, f_v2b with `szx` (raising when facing a bet, c>0): fold equity comes from `frb` with a continuous size factor `0.65+0.55*min(f,2)` (:440), or from `fja` for all-in. No bucket is involved, so this is consistent.
  - River `szr=(0.4,0.8,1.2)` is unchanged in all five.
- :431 `if R >= 0.7*hi: R = hi`: smaller sizes trigger this snap-to-all-in less often. Consistent.
- `min_raise` clamp at :430: with f=0.25 (f_v2b `szx`) or 0.33, the raise is often clamped up to `lo`, so the real fraction is larger than f. The EV uses the clamped R, but `ff` still uses the nominal f. The mismatch is small and conservative (it under-states fold equity).
- `induce` :413-418 and the BB stab model :406-411 assume the **opponent's** bet is 0.6 pot. Our sizes do not matter there.

## Part B: start-up (`python bot.py` with stdin at EOF, 5 runs; a stress match was running in parallel)

| bot | median s | max s |
|---|---|---|
| champion | 0.864 | 0.905 |
| z_s2 | 0.768 | 0.962 |
| z_v2 | 0.884 | 0.982 |
| f_c1 | 0.947 | 0.956 |
| f_v2b | 0.749 | 0.795 |
| f_n45 | 0.737 | 0.781 |

All under 1.5 s: PASS.

## Part C: stress (`run_stress_p1.py --cut`, one bot at a time)

```
SUMMARY z_s2 (cut): matches 24 wins 24 forfeits 0 notices 0 max_time 21.11 s (stage1 12.58, stage2 21.11) unparsed 0
SUMMARY z_v2 (cut): matches 24 wins 24 forfeits 0 notices 0 max_time 39.25 s (stage1 13.90, stage2 39.25) unparsed 0
SUMMARY f_c1 (cut): matches 24 wins 24 forfeits 0 notices 0 max_time 34.11 s (stage1 17.17, stage2 34.11) unparsed 0
SUMMARY f_n45 (cut): matches 24 wins 24 forfeits 0 notices 0 max_time 36.23 s (stage1 15.13, stage2 36.23) unparsed 0
```
PASS. The slowest matches are Stage 2 vs caller/minraise/slow. The banks are 30 s (Stage 1) and 75 s (Stage 2) per leg.

## Part C: outsiders (Stage 2, seed 4242, organiser engine)

| opp | z_s2 net | z_s2 time s | f_c1 net | f_c1 time s |
|---|---|---|---|---|
| x_maniac | +20123 | 19.31 | +23236 | 17.68 |
| x_rock | +5152 | 23.60 | +6304 | 24.60 |
| x_edge | +22178 | 40.71 | +26088 | 41.20 |
| x_gto | **-435** | 24.50 | +330 | 22.50 |
| x_discard | +1616 | 27.64 | +469 | 25.20 |
| x_human | +2272 | 13.04 | +1553 | 11.12 |
| x_adapt | +3545 | 20.24 | +2043 | 20.57 |
| x_punish | +2413 | 24.56 | +1515 | 23.47 |
| x_float | +3772 | 28.62 | +2112 | 24.74 |
| **total** | **+60636 (8/9)** | max 40.71 | **+63650 (9/9)** | max 41.20 |

0 notices, 0 forfeits, 0 unparsed, rc 0 in all 18.

## Fails / risks
1. **No failures** against the pass criteria (forfeits, notices, unparsed, stress wins).
2. Bucket collapse (`bot.py:173-174`, `:169-170`, `:645`): for z_s2, f_n45 (flop + turn) and f_c1 (turn), both menu sizes share bucket 0, so the per-size fold model no longer tells them apart. The risk is low, but this is untested logic drift from the champion.
3. Time: Stage 2 time is up to ~41 s of 75 s (x_edge) and 39 s (z_v2 vs caller), about 2x the earlier p1_bm stress (17 s). Part of this may come from machine load (3 parallel matches). There is headroom, but it is the smallest margin seen.
4. z_s2 lost to x_gto by 435 chips (one seed, Stage 2). That is noise-sized, but it is the only loss. f_c1 won the same match by 330.
