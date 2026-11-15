> Full lab log of the final day, copied from the development tree. Relative links point into that tree and are not part of this repository; the data behind the final tables is in [../evaluation/results](../evaluation/results).

# Final push: evidence (15 Nov 2026)

Champion: `fable5_b_fast` (`../fable5/fable5_b_fast/bot.py`, SHA256 `93847682…3e555143`; every champion record in every run below carries `a_sha` `938476825736`).
Champion menu (profile `t7`): flop/turn `sz=(0.4, 0.8)`, river `szr=(0.4, 0.8, 1.2)`, preflop raise 1.0 pot, `n=600` samples.
All numbers come from `tools/fintab.py`, `tools/pairtab.py`, `tools/peropp.py` run on `results/a4-push-<run>-h*.jsonl` (lab hosts only; `hPC`, `pc*`, `smoke` files not used).
wins = match points (win 1, draw 0.5) of the row on the deals where the champion also played; dW = row wins − champion wins on the same (opponent, seed); d c/h = chips/hand difference; t = paired t of d c/h; p = two-sided sign test on discordant pairs (+ row-only wins / − champion-only wins); clock = paired mean time ratio row/champion; maxT = max seconds per match (both legs).

## 1. Runs

| run | stage | hosts with data | rows | opps | seeds/spec (distinct) | champ clean | champ wins | flagged |
|---|---|---|---|---|---|---|---|---|
| sweep-s2a | 2 | 1 file | 1 (champion) | 126 (spec 127) | 4 (4) | 420 | 371.0 | 12, all vs pool_* |
| sweep-s2b | 2 | 1 file | 1 | 126 (127) | 4 (4) | 465 | 427.0 | 16, all vs pool_* |
| sweep-s2c | 2 | 1 file | 1 | 126 (127) | 4 (4) | 437 | 361.0 | 12, all vs pool_* |
| zp1 | 2 | 19 34 45 60 68 78 | 54 (53 v_* + champion) | 16 | 1-2 (11) | 112 | 91.0 | 0 |
| r1 | 2 | all 6 | 5: champion p1_ps p1_dk p1_bm v_null | 36 | 2-3 (17) | 612 | 495.0 | 0 |
| r2 | 2 | all 6 | 8: champion p1_ps p1_bm p2_psbm p2_rb p2_tv v_szS v_be40 | 29 | 2-4 (22) | 638 | 498.0 | 0 |
| r2b | 2 | none | 11 (spec) | 29 (spec) | 2-4 | 0 | – | no data |
| noshim | 2 | 19 78 | 1 (champion, shim off) | 8 | 12 (24) | 192 | 166.0 | 0 |
| s1a | 1 | all 6 | 5: champion p1_ps p1_bm p2_psbm p2_rb | 36 | 2-4 (22) | 792 | 640.0 | 0 |
| s1z | 1 | all 6 | 54 (53 v_* + champion) | 29 | 1-2 (11) | 319 | 220.0 | 0 |
| r3 | 2 | all 6 | 13 (z_s*, p3_rf*, v_szS) | 29 | 2-3 (17) | 493 | 410.0 | 0 |
| r3b | 2 | all 6 | 12 (z_s1 z_s2 z_t1-9) | 29 | 2-3 (17) | 493 | 405.0 | 0 |
| r3c | 2 | all 6 | 8: champion z_s2 z_u1-6 | 29 | 2-3 (17) | 493 | 378.0 | 0 |
| r3d | 2 | all 6 | 11 (z_s2 z_v1-9) | 31 | 2-3 (17) | 527 | 402.0 | 0 |
| r4 | 2 | all 6 | 6: champion z_s2 z_w1 z_w2 z_w3 z_w5 | 31 | 2-3 (17) | 527 | 424.0 | 0 |
| s1c | 1 | 19 34 45 60 78 (h68 file empty) | 16 | 29 | 2-3 (15) | 435 | 328.0 | 0 |
| s1d | 1 | 68 (re-run of s1c-h68, same rows) | 16 | 29 | 2 (2) | 58 | 43.0 | 0 |
| f1 | 2 | all 6 | 7: champion z_s2 z_v2 f_n45 f_n30 f_v2b f_c1 | 39 | 2-5 (24) | 936 | 779.0 | 0 |
| f2 | 2 | all 6 | 7 (same as f1) | 39 | 2-5 (24) | 936 | 787.5 | 0 |
| f3w | 2 | 19 78 | 5: champion z_s2 z_v2 f_c1 f_n45 | 34 (new, wider field) | 3 (6) | 204 | 184.0 | 0 |
| f1s | 1 | all 6 | 7 (same as f1) | 39 | 2-5 (24) | 936 | 700.0 | 0 |
| f4 | 2 | 19 45 60 68 78 (h34 in spec, no result file) | 6: champion z_s2 f_n56 f_n52 f_n45 f_c1 | 39 | 2-4 (18) | 702 | 591.0 | 0 |
| f4s | 1 | 19 45 60 68 78 (h34 as f4) | 6 (same as f4) | 39 | 2-4 (18) | 702 | 534.0 | 0 |
| f5 | 2 | 19 45 60 68 78 (h34 file empty) | 5: champion z_s2 f_n56 f_n52 f_n45 | 39 | 2-4 (18) | 702 | 577.0 | 0 |
| f5a | 2 | 19 45 60 68 78 (h34 file empty) | 8: champion f_n52 g_t4 g_t3 g_t2 g_t6 g_w3 g_v7 | 39 | 2-4 (18) | 702 | 600.0 | 0 |
| f5a1 | 1 | 19 45 60 68 78, **incomplete** (h45 275/1248, h60 655/1248, h78 1247/1248 records) | 8 (same as f5a) | 39 | 2-4 (14 reached) | 540 | 394.0 | 0 |
| f5b | 2 | – | 9 (spec: champion z_s2 z_t3 z_t4 z_t6 z_t2 z_w3 z_v5 z_v7) | 39 | 2-4 | – | – | not used: incomplete at time of writing (no result files) |
| f6ns | 2 (shim off) | – | 5 (spec: champion z_s2 f_n56 f_n52 f_n45) | 39 | 1-3 | – | – | not used: incomplete at time of writing (no result files) |

- `r2b` was rejected by the lab (seed namespace reuse): all six result files are empty. Incomplete runs: `zp1` h34 (1237 of 1728), h45 (965), h60 (1180), h78 (1654). Because the champion is the last row of each zp1 spec, it has only 112 matches there. The sweep specs list `c33_ad3`, which has no records. `s1c-h68` has 0 of 928 records; `s1d` replaces it.
- Flags: the results have no `error` field (every record has `forfeit`). All 40 forfeits are in `sweep-s2a/b/c`. All are champion vs `pool_aggro`, `pool_jam_top15`, `pool_jam_top30`, `pool_value_only` with `time_a = 0.0`, `wall_s 0.5` and 0.5 points (a draw from an opponent that never started). **No flagged record involves a failure of one of our row bots.** Checked by scanning every lab record for `forfeit: true`, a non-empty `error`, `notices_a > 0`, and forfeits with `time_a > 0`. The only hits were the 40 pool_* forfeits. `notices_a` is 0 in every record of every run.
- f4, f4s, f5, f5a, f5a1 (scan of all 21599 records): 0 forfeits, 0 errors, `notices_a` 0 everywhere. Every spec seed namespace is per run and host (`a4-push-<run>-h<host>-1115`), so pooling runs never merges two records into one (pooled n = sum of the run n).
- `noshim` uses a different seed namespace, so it cannot be paired with a shimmed champion run. 166/192 (0.86) against 8 opponents is shown for reference only.

## 2. Rounds 1 and 2 (`r1`, `r2`, Stage 2; `s1a` Stage 1)

| row | change (build script) | run | n | wins | champ | dW | d c/h | t |
|---|---|---|---|---|---|---|---|---|
| p1_ps | position-split opponent bet rates in the range model | r1 | 612 | 506.0 | 495.0 | +11.0 | +0.025 | +0.77 |
| | | r2 | 638 | 503.0 | 498.0 | +5.0 | +0.030 | +0.88 |
| | | **r1+r2** | 1250 | 1009.0 | 993.0 | **+16.0** | +0.027 | +1.17 |
| p1_bm | call margin scales with the bet: `margin*min(pot, 2c)` on flop/turn | r1 | 612 | 501.0 | 495.0 | +6.0 | +0.044 | +1.27 |
| | | r2 | 638 | 491.0 | 498.0 | −7.0 | −0.051 | −1.55 |
| | | **r1+r2** | 1250 | 992.0 | 993.0 | **−1.0** | −0.005 | −0.19 |
| p1_dk | keep model learned from showdowns | r1 | 612 | 497.0 | 495.0 | +2.0 | −0.011 | −0.44 |
| v_null | identical-play copy | r1 | 612 | 497.0 | 495.0 | +2.0 | +0.003 | +0.30 |
| p2_rb | flop/turn bets price in his learned raise rate | r2 | 638 | 491.0 | 498.0 | −7.0 | −0.024 | −0.63 |
| p2_tv | river menu gets a 0.25-pot size | r2 | 638 | 500.0 | 498.0 | +2.0 | +0.050 | +2.77 |
| p2_psbm | p1_ps + p1_bm | r2 | 638 | 498.0 | 498.0 | 0.0 | +0.012 | +0.34 |
| v_szS | `sz=(0.33, 0.66)` | r2 | 638 | 502.0 | 498.0 | +4.0 | +0.131 | +3.32 |
| v_be40 | river bluff threshold e<0.40 (was 0.45) | r2 | 638 | 493.0 | 498.0 | −5.0 | +0.038 | +0.95 |

Stage 1 (`s1a`, n=792, champion 640.0): p1_bm +1.5 (t −0.44), p1_ps −5.0 (+0.12), p2_psbm −8.0 (+0.09), p2_rb −9.0 (−2.18). No sign test in rounds 1-2 is below p=0.27. None of these mechanisms changes match wins.

## 3. Parameter sweep (53 single-parameter variants, [sweep/MANIFEST.md](sweep/MANIFEST.md))

`zp1` (Stage 2, 16 opponents, n=112 each, champion 91.0) and `s1z` (Stage 1, 29 opponents, n=319, champion 220.0). Ties in dW are ordered as fintab prints them.

| zp1 top 8 | dW | d c/h | t | | s1z top 8 | dW | d c/h | t |
|---|---|---|---|---|---|---|---|---|
| v_in15 (induce 1.5) | +8.0 | +0.117 | +1.63 | | v_vm34 (vmax 0.34) | +16.5 | +0.161 | +2.42 |
| v_sl55 (steeper raise-size slope) | +7.0 | +0.081 | +0.86 | | v_bp70 (bluff_p 0.7) | +16.5 | +0.167 | +2.33 |
| v_cf02 (call-fold floor 0.02) | +7.0 | −0.010 | −0.16 | | v_szS (sz 0.33/0.66) | +16.0 | +0.209 | +2.88 |
| v_sl15 (flatter slope) | +6.0 | +0.058 | +0.76 | | v_bk90 (bluff_k 0.9) | +16.0 | +0.249 | +2.79 |
| v_gw04 (sigmoid width 0.04) | +6.0 | +0.048 | +0.62 | | v_gw04 | +12.5 | +0.011 | +0.17 |
| v_szS | +5.0 | +0.086 | +0.96 | | v_cf02 | +10.5 | +0.060 | +1.52 |
| v_rt05 (raise threshold 0.05 pot) | +5.0 | −0.033 | −0.37 | | v_cd85 (check-EV factor) | +10.0 | +0.049 | +0.88 |
| v_n1500 (1500 samples, clock x1.71) | +5.0 | +0.283 | +2.68 | | v_be40 | +10.0 | +0.120 | +1.37 |
| **bottom 5** | | | | | **bottom 5** | | | |
| v_bl12 (bluff0 0.12) | −5.0 | −0.041 | −0.74 | | v_ema06 (slower EMA) | −12.5 | −0.228 | −3.50 |
| v_bk50 (bluff_k 0.5) | −5.0 | −0.070 | −0.77 | | v_be50 | −13.0 | −0.213 | −2.59 |
| v_gw09 | −6.0 | −0.141 | −1.64 | | v_sz3 (sz 0.33/0.66/1.1) | −13.5 | −0.083 | −1.02 |
| v_exS (larger S priors) | −8.0 | −0.145 | −1.72 | | v_gw09 | −13.5 | −0.156 | −2.46 |
| v_szL (sz 0.5/1.0) | −16.5 | −0.371 | −4.09 | | v_pf130 (preflop 1.3 pot) | −24.5 | −0.413 | −4.69 |

v_null vs champion: zp1 +1.0 (1/0 discordant, t −0.64), s1z −2.0 (2/4). Against v_null as the base (zp1, larger n per row), v_szS is +10.0 (n=160, p=0.064, t +2.94) and v_szL −16.5 (p=0.002).
Pattern: the only consistent signal at both stages is bet size. Smaller flop/turn sizes (v_szS) are in the top 8 at both stages, larger ones (v_szL) are clearly worst at Stage 2, and v_pf130 is worst at Stage 1. Most other single parameters sit within ±8 wins, inside the noise, and the bluff parameters swap sign between stages.

## 4. Bet-size menu rounds

Menu = flop/turn `sz` (raises `szx`, turn `szt` where split) | river `szr` | preflop size; "–" = champion value.

**r3** (Stage 2, champion 410.0/493, maxT 11.7)
| row | menu | n | wins | dW | +/- p | d c/h | t | maxT |
|---|---|---|---|---|---|---|---|---|
| z_s10 | 0.4 | 493 | 436.0 | +26.0 | 0.003 | +0.320 | +6.45 | 13.6 |
| z_s2 | 0.33/0.5 | 493 | 435.0 | +25.0 | 0.002 | +0.292 | +6.28 | 14.3 |
| z_s1 | 0.25/0.5 | 493 | 422.0 | +12.0 | 0.188 | +0.279 | +5.44 | 13.2 |
| z_s6 | 0.33/0.66, pf 0.75 | 493 | 431.5 | +21.5 | 0.020 | +0.192 | +3.69 | 12.9 |
| z_s5 | 0.33/0.66, river 0.25/0.4/0.8/1.2 | 493 | 428.0 | +18.0 | 0.038 | +0.254 | +5.52 | 13.8 |
| z_s7 | z_s5 + pf 0.75 | 493 | 428.0 | +18.0 | 0.060 | +0.211 | +4.03 | 13.3 |
| z_s8 | 0.3/0.6 | 493 | 424.0 | +14.0 | 0.135 | +0.223 | +4.66 | 12.2 |
| v_szS | 0.33/0.66 | 493 | 420.0 | +10.0 | 0.289 | +0.185 | +3.82 | 12.6 |
| z_s4 | 0.33/0.66, river 0.33/0.66/1.0 | 493 | 415.0 | +5.0 | 0.640 | +0.180 | +3.82 | 12.8 |
| p3_rf30s | raise-bluff floor 0.30 + 0.33/0.66 | 493 | 411.0 | +1.0 | 1.000 | +0.093 | +1.81 | 13.5 |
| p3_rf45 | raise-bluff floor 0.45 (no menu change) | 493 | 402.0 | −8.0 | 0.461 | −0.110 | −2.33 | 12.1 |
| p3_rf25 | raise-bluff floor 0.25 | 493 | 398.0 | −12.0 | 0.207 | −0.086 | −1.89 | 13.5 |

**r3b** (Stage 2, champion 405.0/493)
| row | menu | n | wins | dW | p | d c/h | t | maxT |
|---|---|---|---|---|---|---|---|---|
| z_t3 | 0.25 | 493 | 457.0 | +52.0 | 0.000 | +0.637 | +10.95 | 14.6 |
| z_t4 | 0.33 | 493 | 452.0 | +47.0 | 0.000 | +0.489 | +8.84 | 12.5 |
| z_t6 | 0.15/0.33 | 493 | 451.0 | +46.0 | 0.000 | +0.653 | +11.62 | 14.8 |
| z_t2 | 0.25/0.4 | 493 | 448.0 | +43.0 | 0.000 | +0.543 | +9.96 | 14.5 |
| z_t1 | 0.2/0.4 | 493 | 446.0 | +41.0 | 0.000 | +0.540 | +9.82 | 14.8 |
| z_t8 | 0.25/0.5, pf 0.75 | 493 | 443.5 | +38.5 | 0.000 | +0.498 | +9.02 | 15.2 |
| z_t9 | 0.25/0.5, river 0.25/0.5/1.0 | 493 | 433.0 | +28.0 | 0.002 | +0.534 | +10.51 | 13.4 |
| z_t5 | 0.2/0.5 | 493 | 432.0 | +27.0 | 0.005 | +0.443 | +8.26 | 14.4 |
| z_t7 | 0.25/0.5, river 0.25/0.4/0.8/1.2 | 493 | 431.0 | +26.0 | 0.007 | +0.460 | +8.87 | 14.6 |
| z_s1 | 0.25/0.5 | 493 | 429.0 | +24.0 | 0.012 | +0.442 | +8.74 | 13.2 |
| z_s2 | 0.33/0.5 | 493 | 427.0 | +22.0 | 0.020 | +0.419 | +8.65 | 13.7 |

**r3c** (Stage 2, champion 378.0/493)
| row | menu | n | wins | dW | p | d c/h | t | maxT |
|---|---|---|---|---|---|---|---|---|
| z_u6 | 0.25/0.5, river 0.25/0.4/0.8/1.2, pf 0.75 | 493 | 444.0 | +66.0 | 0.000 | +0.564 | +9.40 | 15.4 |
| z_u5 | 0.3/0.5, pf 0.75 | 493 | 436.0 | +58.0 | 0.000 | +0.450 | +7.88 | 15.0 |
| z_u4 | 0.33/0.5, river 0.25/0.4/0.8/1.2, pf 0.75 | 493 | 429.5 | +51.5 | 0.000 | +0.507 | +8.90 | 14.8 |
| z_s2 | 0.33/0.5 | 493 | 428.0 | +50.0 | 0.000 | +0.406 | +8.84 | 13.6 |
| z_u1 | 0.33/0.5, pf 0.75 | 493 | 425.0 | +47.0 | 0.000 | +0.410 | +7.50 | 14.6 |
| z_u3 | 0.33/0.5, pf 0.5 | 493 | 424.0 | +46.0 | 0.000 | +0.312 | +5.68 | 14.0 |
| z_u2 | 0.33/0.5, pf 0.6 | 493 | 415.0 | +37.0 | 0.001 | +0.350 | +5.93 | 15.0 |

**r3d** (Stage 2, champion 402.0/527)
| row | menu | n | wins | dW | p | d c/h | t | maxT |
|---|---|---|---|---|---|---|---|---|
| z_v5 | flop 0.33/0.5, turn 0.4/0.8 | 527 | 460.0 | +58.0 | 0.000 | +0.441 | +10.72 | 13.1 |
| z_v7 | 0.33/0.5, river 0.33/0.5/0.8/1.2 | 527 | 459.0 | +57.0 | 0.000 | +0.554 | +11.99 | 12.2 |
| z_s2 | 0.33/0.5 | 527 | 451.0 | +49.0 | 0.000 | +0.516 | +11.22 | 14.4 |
| z_v8 | 0.33/0.5, river 0.4/0.8 | 527 | 451.0 | +49.0 | 0.000 | +0.529 | +11.57 | 13.3 |
| z_v2 | bets 0.4/0.8, raises 0.33/0.5 | 527 | 445.0 | +43.0 | 0.000 | +0.341 | +8.93 | 13.0 |
| z_v9 | 0.25/0.4/0.6 | 527 | 439.0 | +37.0 | 0.000 | +0.338 | +7.43 | 15.0 |
| z_v1 | bets 0.33/0.5, raises 0.4/0.8 | 527 | 435.0 | +33.0 | 0.001 | +0.362 | +7.94 | 12.4 |
| z_v6 | flop 0.4/0.8, turn 0.33/0.5 | 527 | 431.0 | +29.0 | 0.001 | +0.108 | +3.15 | 11.4 |
| z_v4 | bets 0.33/0.5, raises 0.5/1.0 | 527 | 423.0 | +21.0 | 0.035 | +0.189 | +4.21 | 14.5 |
| z_v3 | 0.33/0.5/0.8 | 527 | 420.0 | +18.0 | 0.085 | +0.131 | +3.20 | 13.1 |

**r4** (Stage 2, champion 424.0/527; all on 0.33/0.5)
| row | menu + mechanism | n | wins | dW | p | d c/h | t | maxT |
|---|---|---|---|---|---|---|---|---|
| z_w3 | + separate fold rate for the 0.33/0.5 sizes | 527 | 452.0 | +28.0 | 0.004 | +0.382 | +8.17 | 14.4 |
| z_w2 | + p1_bm | 527 | 445.0 | +21.0 | 0.022 | +0.408 | +9.07 | 12.9 |
| z_w5 | + p1_ps + p1_bm | 527 | 444.0 | +20.0 | 0.033 | +0.288 | +6.23 | 13.9 |
| z_w1 | + p1_ps | 527 | 437.0 | +13.0 | 0.187 | +0.287 | +6.29 | 14.2 |
| z_s2 | none | 527 | 427.0 | +3.0 | 0.836 | +0.296 | +6.32 | 13.0 |

**s1c + s1d** (Stage 1, pooled because s1d is the h68 part; champion 371.0/493, maxT 4.8; q_* = 0.33/0.66 + listed)
| row | menu / change | n | wins | dW | p | d c/h | t | maxT |
|---|---|---|---|---|---|---|---|---|
| q_f | + bluff_k 0.9, vmax 0.34 | 493 | 386.5 | +15.5 | 0.141 | +0.257 | +3.67 | 5.2 |
| q_b | + bluff_k 0.9, bluff_p 0.7 | 493 | 378.0 | +7.0 | 0.562 | +0.273 | +3.83 | 4.1 |
| z_s5 | 0.33/0.66, river 0.25/0.4/0.8/1.2 | 493 | 377.0 | +6.0 | 0.556 | +0.146 | +2.34 | 4.9 |
| q_a | + bluff_k 0.9 | 493 | 376.0 | +5.0 | 0.675 | +0.338 | +5.03 | 5.1 |
| q_e | + vmax 0.34 | 493 | 375.0 | +4.0 | 0.755 | +0.045 | +0.69 | 5.0 |
| z_s8 | 0.3/0.6 | 493 | 375.0 | +4.0 | 0.747 | +0.146 | +2.24 | 4.8 |
| v_bk90 | bluff_k 0.9 (menu –) | 493 | 374.0 | +3.0 | 0.841 | +0.076 | +1.08 | 5.1 |
| v_szS | 0.33/0.66 | 493 | 373.0 | +2.0 | 0.915 | +0.103 | +1.66 | 5.2 |
| z_s1 | 0.25/0.5 | 493 | 371.0 | 0.0 | 1.000 | +0.249 | +3.64 | 4.7 |
| z_s7 | z_s5 + pf 0.75 | 493 | 369.0 | −2.0 | 0.919 | +0.041 | +0.61 | 4.4 |
| q_d | + bluff_p 0.7 | 493 | 366.0 | −5.0 | 0.688 | +0.034 | +0.52 | 4.5 |
| z_s6 | 0.33/0.66, pf 0.75 | 493 | 366.0 | −5.0 | 0.688 | +0.005 | +0.07 | 4.6 |
| q_c | + bluff_k 0.9, bluff_p 0.7, vmax 0.34 | 493 | 362.0 | −9.0 | 0.444 | +0.112 | +1.45 | 5.6 |
| v_vm34 | vmax 0.34 (menu –) | 493 | 350.0 | −21.0 | 0.026 | −0.076 | −1.29 | 4.3 |
| v_bp70 | bluff_p 0.7 (menu –) | 493 | 347.5 | −23.5 | 0.015 | −0.153 | −2.66 | 4.7 |

What the data say:
- At Stage 2 every menu smaller than 0.4/0.8 gains chips (t +3 to +12). Match wins gain from about +20 to +66 per ~500, and the size of the gain moves with the champion's own score in that run (r3c 378 → z_s2 +50; r4 424 → z_s2 +3). No single small menu is consistently best. z_s2 (0.33/0.5) is in the middle of every run, and the single sizes 0.25 / 0.33 lead r3b.
- r3d split: both bets alone (z_v1 +33) and raises alone (z_v2 +43) carry part of the gain. The flop carries most of it: flop-only z_v5 (+58, t +10.7) matches the full z_s2, while turn-only z_v6 is +29 with only +0.108 c/h. Adding back a 0.8 size (z_v3) or bigger raises (z_v4) removes most of the gain.
- Preflop size: pf 0.75/0.6/0.5 (z_u*, z_s6/7, z_t8) adds nothing clear over the same flop/turn menu at Stage 2 (z_u1 +47 vs z_s2 +50 on the same deals) and costs at Stage 1 (z_s6 −5, z_s7 −2). It also raises the clock (×1.25-1.35). River size changes (z_v7, z_v8, z_u4/6, z_t7/9) are within the noise of the base menu.
- Stage 1 (400 hands) shows no reliable win gain from any menu (best q_f +15.5, p=0.14), even though chips rise. v_vm34 and v_bp70, top-4 in s1z, are bottom-2 here, which suggests s1z's top list is noise.

## 5. Finalists

Finalist menus ([build_final.py](build_final.py)): z_s2 0.33/0.5; f_n45 = z_s2 with `n=450`; f_n30 = `n=300`; z_v2 bets 0.4/0.8, raises 0.33/0.5; f_v2b bets 0.4/0.8, raises 0.25/0.5; f_c1 flop bets 0.4/0.8, turn bets 0.33/0.5, raises 0.33/0.5. f_v2b and f_n30 are not in f3w.

| run | row | n | wins | champ | dW | +/- | p | d c/h | t | clock | maxT | flag | notices |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| f1 | z_s2 | 936 | 835.0 | 779.0 | +56.0 | 91/35 | 0.000 | +0.175 | +3.94 | 1.088 | 19.8 | 0 | 0 |
| f1 | f_n45 | 936 | 826.0 | 779.0 | +47.0 | 98/51 | 0.000 | +0.109 | +2.24 | 0.954 | 21.3 | 0 | 0 |
| f1 | f_c1 | 936 | 820.0 | 779.0 | +41.0 | 71/30 | 0.000 | +0.113 | +3.22 | 1.011 | 19.9 | 0 | 0 |
| f1 | f_v2b | 936 | 818.0 | 779.0 | +39.0 | 75/36 | 0.000 | +0.214 | +7.09 | 0.991 | 17.9 | 0 | 0 |
| f1 | f_n30 | 936 | 817.0 | 779.0 | +38.0 | 99/61 | 0.003 | +0.043 | +0.88 | 0.827 | 18.0 | 0 | 0 |
| f1 | z_v2 | 936 | 807.0 | 779.0 | +28.0 | 67/39 | 0.008 | +0.178 | +6.00 | 1.007 | 21.6 | 0 | 0 |
| f2 | z_s2 | 936 | 852.0 | 787.5 | +64.5 | 90/26 | 0.000 | +0.167 | +3.70 | 1.116 | 17.2 | 0 | 0 |
| f2 | f_c1 | 936 | 834.0 | 787.5 | +46.5 | 75/28 | 0.000 | +0.073 | +2.06 | 1.004 | 19.0 | 0 | 0 |
| f2 | f_v2b | 936 | 830.0 | 787.5 | +42.5 | 78/36 | 0.000 | +0.179 | +5.90 | 1.033 | 18.6 | 0 | 0 |
| f2 | f_n45 | 936 | 826.0 | 787.5 | +38.5 | 99/60 | 0.002 | +0.087 | +1.71 | 0.976 | 16.0 | 0 | 0 |
| f2 | z_v2 | 936 | 826.0 | 787.5 | +38.5 | 71/33 | 0.000 | +0.170 | +5.88 | 1.027 | 18.5 | 0 | 0 |
| f2 | f_n30 | 936 | 803.0 | 787.5 | +15.5 | 90/74 | 0.241 | −0.075 | −1.45 | 0.853 | 16.9 | 0 | 0 |
| f3w | z_s2 | 204 | 194.0 | 184.0 | +10.0 | 13/3 | 0.021 | +0.307 | +1.91 | 1.094 | 17.0 | 0 | 0 |
| f3w | f_n45 | 204 | 193.0 | 184.0 | +9.0 | 13/4 | 0.049 | +0.318 | +1.89 | 0.985 | 15.7 | 0 | 0 |
| f3w | z_v2 | 204 | 192.0 | 184.0 | +8.0 | 12/4 | 0.077 | +0.450 | +4.42 | 1.001 | 17.8 | 0 | 0 |
| f3w | f_c1 | 204 | 190.0 | 184.0 | +6.0 | 11/5 | 0.210 | +0.111 | +0.91 | 1.022 | 16.1 | 0 | 0 |
| **S2 pool** | z_s2 | 2076 | 1881.0 | 1750.5 | **+130.5** | 194/64 | 0.000 | +0.184 | +5.65 | 1.101 | 19.8 | 0 | 0 |
| S2 pool | f_n45 | 2076 | 1845.0 | 1750.5 | +94.5 | 210/115 | 0.000 | +0.119 | +3.35 | 0.968 | 21.3 | 0 | 0 |
| S2 pool | f_c1 | 2076 | 1844.0 | 1750.5 | +93.5 | 157/63 | 0.000 | +0.095 | +3.73 | 1.009 | 19.9 | 0 | 0 |
| S2 pool | z_v2 | 2076 | 1825.0 | 1750.5 | +74.5 | 150/76 | 0.000 | +0.201 | +9.46 | 1.015 | 21.6 | 0 | 0 |
| S2 pool (f1+f2) | f_v2b | 1872 | 1648.0 | 1566.5 | +81.5 | 153/72 | 0.000 | +0.197 | +9.18 | 1.012 | 18.6 | 0 | 0 |
| S2 pool (f1+f2) | f_n30 | 1872 | 1620.0 | 1566.5 | +53.5 | 189/135 | 0.003 | −0.016 | −0.45 | 0.840 | 18.0 | 0 | 0 |
| **f1s (S1)** | f_n45 | 936 | 777.0 | 700.0 | **+77.0** | 142/65 | 0.000 | +0.175 | +2.76 | 1.022 | 7.4 | 0 | 0 |
| f1s | z_s2 | 936 | 766.0 | 700.0 | +66.0 | 117/51 | 0.000 | +0.146 | +2.60 | 1.133 | 7.0 | 0 | 0 |
| f1s | f_n30 | 936 | 744.0 | 700.0 | +44.0 | 123/79 | 0.002 | +0.088 | +1.29 | 0.862 | 6.7 | 0 | 0 |
| f1s | z_v2 | 936 | 735.5 | 700.0 | +35.5 | 78/42 | 0.001 | +0.164 | +4.32 | 1.035 | 9.7 | 0 | 0 |
| f1s | f_v2b | 936 | 734.0 | 700.0 | +34.0 | 78/44 | 0.003 | +0.125 | +2.97 | 1.011 | 6.8 | 0 | 0 |
| f1s | f_c1 | 936 | 724.0 | 700.0 | +24.0 | 90/66 | 0.065 | +0.013 | +0.27 | 1.072 | 7.8 | 0 | 0 |

Champion maxT: f1 19.9, f2 19.5, f3w 16.6, f1s 7.7 s; champion flags and notices 0. No finalist is worse than the champion in match wins in any run.
**Per group** (pairtab `--groups groups.json`, S2 pool f1+f2+f3w; dW, d c/h, t). [groups.json](groups.json) covers 34 of the 39 f1/f2 opponents. Outside any group: `ext_camello_cfr`, `ext_week3`, `fp_adaptive`, `fp_nit`, `v_null`. It covers **none** of the 34 f3w opponents, so the group lines are f1+f2 only.

| group (n) | z_s2 | f_n45 | f_c1 | z_v2 |
|---|---|---|---|---|
| family (528) | +53.5, +0.311, +6.86 | +34.5, +0.198, +3.49 | +43.5, +0.188, +4.16 | +32.5, +0.198, +4.63 |
| c32fam (336) | +39.0, +0.686, +10.21 | +33.0, +0.575, +7.93 | +32.0, +0.527, +8.38 | +25.0, +0.523, +7.75 |
| astra (288) | +7.0, +0.144, +4.07 | +6.0, +0.109, +2.34 | +5.0, +0.025, +0.85 | +4.0, +0.099, +3.28 |
| outsider (384) | +2.0, **−0.331**, −4.41 | +3.0, **−0.365**, −4.54 | +2.0, −0.152, −2.77 | +1.0, +0.029, +0.75 |
| punish (96) | +14.0, +1.785, +17.19 | +14.0, +1.791, +17.81 | +9.0, +0.668, +9.14 | +3.0, −0.118, −2.09 |

**Per opponent** (`peropp.py`, S2 pool; n=48 for f1/f2 opponents, 6 for f3w-only opponents). Opponents where the bot gains or loses ≥ 3 wins, or loses ≥ 1.0 c/h:

| opponent | n | z_s2 wins (vs champ) | z_s2 c/h (vs champ) | f_n45 wins | f_n45 c/h |
|---|---|---|---|---|---|
| sh_champ_agg | 48 | 29 vs 16 | +0.33 vs −0.29 | 28 vs 16 | +0.19 vs −0.29 |
| c32_slowplay | 48 | 45 vs 33 | +1.61 vs +0.78 | 42 vs 33 | +1.26 vs +0.78 |
| x_punish | 48 | 48 vs 36 | +2.86 vs +0.96 | 47 vs 36 | +2.87 vs +0.96 |
| fable_h2 | 48 | 32 vs 24 | +0.52 vs +0.13 | 31 vs 24 | +0.30 vs +0.13 |
| c34 / c35_base | 48 / 48 | 45 vs 39 / 46 vs 41 | +2.06 vs +1.25 / +2.08 vs +1.27 | 45 vs 39 / 47 vs 41 | +2.09 / +2.01 |
| nova_tight | 48 | 42 vs 36.5 | +1.45 vs +0.96 | 42 vs 36.5 | +1.40 vs +0.96 |
| fable5_b (= v_null, identical rows) | 48 | 34 vs 29 | +0.43 vs +0.13 | **24 vs 29** | +0.02 vs +0.13 |
| fp_adaptive | 48 | 48 vs 48 | **+13.48 vs +17.37** | 48 vs 48 | **+13.25 vs +17.37** |
| x_rock / x_edge | 48 / 48 | 48 vs 48 / 48 vs 48 | +5.81 vs +8.28 / +25.01 vs +26.97 | 48 vs 48 / 48 vs 48 | +5.75 / +24.93 |
| z_opus_quick_2, random, fp_equity_threshold, fp_station, z_opus_serious_1 | 6 each | all 6 vs 6 | −1.1 to −2.6 c/h each | all 6 vs 6 | −1.7 to −2.7 c/h each |

Opponents with FEWER wins than the champion: **z_s2**: astra_eq (46 vs 47), x_human (47 vs 48), x_adapt (47 vs 48), t3crm (5 vs 6). **f_n45**: fable5_b (24 vs 29) and v_null (24 vs 29), z_opus_serious_2 (46 vs 47), nova_t7 (38 vs 39), astra_hybrid (47 vs 48), x_human (47 vs 48), t3crm (5 vs 6), c20 (5 vs 6), v2_exploit (5 vs 6). Totals: z_s2 1881.0 vs 1750.5, f_n45 1845.0 vs 1750.5.
The chip losses of the small-menu bots are all against opponents the champion already beats by 5-27 c/h (passive or over-folding bots: fp_adaptive, x_rock, x_edge, random, fp_station). No match is lost there.

### 5b. Later finalist runs (f4, f4s, f5, f5a, f5a1)

New rows ([build_final.py](build_final.py)): f_n52 = 0.33/0.5 with `n=525`, f_n56 = `n=560`; g_t4 `sz=(0.33,)` n=525, g_t3 `sz=(0.25,)` n=450, g_t2 0.25/0.4 n=450, g_t6 0.15/0.33 n=420, g_w3 0.33/0.5 n=525 + separate fold bucket (build_p6 FB patch), g_v7 0.33/0.5 + river 0.33/0.5/0.8/1.2 n=525. Base = champion unless stated. f5a1 is incomplete (section 1), so its rows have different n.

| run | row | n | wins | champ | dW | +/- | p | d c/h | t | clock | maxT | flag | notices |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| f4 | f_n52 | 702 | 647.0 | 591.0 | +56.0 | 82/26 | 0.000 | +0.270 | +4.77 | 1.007 | 18.9 | 0 | 0 |
| f4 | f_n56 | 702 | 639.0 | 591.0 | +48.0 | 74/26 | 0.000 | +0.212 | +3.73 | 1.012 | 17.4 | 0 | 0 |
| f4 | f_n45 | 702 | 637.0 | 591.0 | +46.0 | 78/32 | 0.000 | +0.263 | +4.65 | 0.933 | 18.4 | 0 | 0 |
| f4 | f_c1 | 702 | 636.0 | 591.0 | +45.0 | 73/28 | 0.000 | +0.143 | +3.43 | 0.974 | 17.2 | 0 | 0 |
| f4 | z_s2 | 702 | 620.0 | 591.0 | +29.0 | 68/39 | 0.007 | +0.200 | +3.62 | 1.059 | 22.9 | 0 | 0 |
| f5 | f_n56 | 702 | 620.0 | 577.0 | +43.0 | 75/32 | 0.000 | +0.122 | +2.18 | 1.060 | 21.1 | 0 | 0 |
| f5 | f_n45 | 702 | 614.0 | 577.0 | +37.0 | 76/39 | 0.001 | +0.098 | +1.75 | 0.977 | 17.4 | 0 | 0 |
| f5 | z_s2 | 702 | 611.0 | 577.0 | +34.0 | 74/40 | 0.002 | +0.066 | +1.20 | 1.112 | 17.5 | 0 | 0 |
| f5 | f_n52 | 702 | 608.0 | 577.0 | +31.0 | 63/32 | 0.002 | +0.139 | +2.54 | 1.025 | 16.5 | 0 | 0 |
| f5a | g_t4 | 702 | 643.5 | 600.0 | +43.5 | 69/25 | 0.000 | −0.056 | −0.76 | 1.090 | 17.3 | 0 | 0 |
| f5a | g_v7 | 702 | 642.0 | 600.0 | +42.0 | 67/25 | 0.000 | +0.222 | +3.86 | 1.038 | 16.4 | 0 | 0 |
| f5a | g_t3 | 702 | 636.0 | 600.0 | +36.0 | 76/40 | 0.001 | −0.210 | −2.30 | 1.079 | 18.5 | 0 | 0 |
| f5a | f_n52 | 702 | 634.0 | 600.0 | +34.0 | 62/28 | 0.000 | +0.131 | +2.34 | 1.039 | 18.1 | 0 | 0 |
| f5a | g_t6 | 702 | 633.0 | 600.0 | +33.0 | 70/37 | 0.002 | −0.016 | −0.21 | 1.054 | 18.6 | 0 | 0 |
| f5a | g_t2 | 702 | 629.0 | 600.0 | +29.0 | 67/38 | 0.006 | +0.064 | +0.90 | 1.042 | 18.1 | 0 | 0 |
| f5a | g_w3 | 702 | 624.0 | 600.0 | +24.0 | 65/41 | 0.025 | +0.103 | +1.86 | 1.046 | 17.3 | 0 | 0 |
| **f4s (S1)** | f_n52 | 702 | 573.0 | 534.0 | +39.0 | 95/56 | 0.002 | +0.056 | +0.75 | 1.044 | 7.4 | 0 | 0 |
| f4s | f_n45 | 702 | 567.0 | 534.0 | +33.0 | 87/54 | 0.007 | +0.013 | +0.18 | 0.979 | 6.5 | 0 | 0 |
| f4s | f_n56 | 702 | 567.0 | 534.0 | +33.0 | 83/50 | 0.005 | +0.037 | +0.51 | 1.054 | 7.4 | 0 | 0 |
| f4s | z_s2 | 702 | 566.0 | 534.0 | +32.0 | 80/48 | 0.006 | +0.026 | +0.36 | 1.136 | 8.5 | 0 | 0 |
| f4s | f_c1 | 702 | 564.5 | 534.0 | +30.5 | 72/42 | 0.006 | +0.050 | +0.92 | 1.029 | 8.0 | 0 | 0 |
| **f5a1 (S1)** | g_t2 | 507 | 401.0 | 369.0 | +32.0 | 76/44 | 0.004 | −0.000 | −0.00 | 1.092 | 7.5 | 0 | 0 |
| f5a1 | g_t4 | 507 | 396.5 | 369.0 | +27.5 | 77/50 | 0.021 | −0.117 | −1.13 | 1.132 | 6.7 | 0 | 0 |
| f5a1 | f_n52 | 508 | 395.5 | 369.0 | +26.5 | 71/45 | 0.020 | +0.119 | +1.33 | 1.074 | 7.5 | 0 | 0 |
| f5a1 | g_v7 | 471 | 366.0 | 349.0 | +17.0 | 54/37 | 0.093 | +0.137 | +1.48 | 1.067 | 7.4 | 0 | 0 |
| f5a1 | g_w3 | 504 | 384.0 | 367.0 | +17.0 | 63/46 | 0.125 | +0.105 | +1.20 | 1.087 | 7.3 | 0 | 0 |
| f5a1 | g_t3 | 507 | 385.0 | 369.0 | +16.0 | 75/59 | 0.195 | −0.393 | −3.21 | 1.164 | 7.6 | 0 | 0 |
| f5a1 | g_t6 | 505 | 383.0 | 368.0 | +15.0 | 78/63 | 0.238 | −0.141 | −1.23 | 1.161 | 7.2 | 0 | 0 |

Champion: f4 702 matches, maxT 17.2; f5 702, 17.4; f5a 702, 18.9; f4s 702, 7.9; f5a1 540, 7.4 s; flags and notices 0.

**g_* vs f_n52 on the same deals** (base f_n52; f5a: f_n52 634.0/702; f5a1: f_n52 395.5/508):

| row | f5a dW | p | d c/h | t | clock | f5a1 dW | p | d c/h | t | clock |
|---|---|---|---|---|---|---|---|---|---|---|
| g_t4 | +9.5 | 0.328 | −0.188 | −4.37 | 1.049 | +1.0 | 1.000 | −0.238 | −3.56 | 1.054 |
| g_v7 | +8.0 | 0.215 | +0.091 | +4.20 | 0.999 | −6.5 | 0.286 | +0.036 | +1.27 | 0.982 |
| g_t3 | +2.0 | 0.914 | −0.341 | −5.58 | 1.038 | −10.5 | 0.343 | −0.513 | −5.83 | 1.083 |
| g_t6 | −1.0 | 1.000 | −0.147 | −2.94 | 1.014 | −11.5 | 0.347 | −0.264 | −3.29 | 1.083 |
| g_t2 | −5.0 | 0.649 | −0.068 | −1.62 | 1.002 | +5.5 | 0.598 | −0.120 | −1.80 | 1.016 |
| g_w3 | −10.0 | 0.237 | −0.028 | −0.91 | 1.007 | −9.5 | 0.356 | −0.020 | −0.40 | 1.006 |

**Pooled lines** (base champion; pools of separate files concatenated, n = sum of runs):

| pool | row | n | wins | champ | dW | +/- | p | d c/h | t | clock | maxT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S2 f1+f2+f4+f5 | f_n45 | 3276 | 2903.0 | 2734.5 | +168.5 | 351/182 | 0.000 | +0.133 | +5.06 | 0.960 | 21.3 |
| S2 f1+f2+f4+f5 | z_s2 | 3276 | 2918.0 | 2734.5 | +183.5 | 323/140 | 0.000 | +0.155 | +6.28 | 1.095 | 22.9 |
| S2 f1+f2+f3w+f4+f5 | f_n45 | 3480 | 3096.0 | 2918.5 | +177.5 | 364/186 | 0.000 | +0.144 | +5.41 | 0.962 | 21.3 |
| S2 f1+f2+f3w+f4+f5 | z_s2 | 3480 | 3112.0 | 2918.5 | +193.5 | 336/143 | 0.000 | +0.164 | +6.53 | 1.095 | 22.9 |
| S2 f4+f5 | f_n56 | 1404 | 1259.0 | 1168.0 | +91.0 | 149/58 | 0.000 | +0.167 | +4.19 | 1.036 | 21.1 |
| S2 f4+f5 | f_n52 | 1404 | 1255.0 | 1168.0 | +87.0 | 145/58 | 0.000 | +0.205 | +5.19 | 1.016 | 18.9 |
| S2 f4+f5 | f_n45 | 1404 | 1251.0 | 1168.0 | +83.0 | 154/71 | 0.000 | +0.181 | +4.53 | 0.955 | 18.4 |
| S2 f4+f5 | z_s2 | 1404 | 1231.0 | 1168.0 | +63.0 | 142/79 | 0.000 | +0.133 | +3.41 | 1.085 | 22.9 |
| S2 f4+f5+f5a | f_n52 | 2106 | 1889.0 | 1768.0 | +121.0 | 207/86 | 0.000 | +0.180 | +5.58 | 1.024 | 18.9 |
| S1 f1s+f4s | f_n45 | 1638 | 1344.0 | 1234.0 | +110.0 | 229/119 | 0.000 | +0.106 | +2.22 | 1.003 | 7.4 |
| S1 f1s+f4s | z_s2 | 1638 | 1332.0 | 1234.0 | +98.0 | 197/99 | 0.000 | +0.095 | +2.13 | 1.135 | 8.5 |
| S1 f1s+f4s | f_c1 | 1638 | 1288.5 | 1234.0 | +54.5 | 162/108 | 0.001 | +0.029 | +0.81 | 1.053 | 8.0 |
| S1 f4s+f5a1 | f_n52 | 1210 | 968.5 | 903.0 | +65.5 | 166/101 | 0.000 | +0.082 | +1.43 | **1.057** | 7.5 |

## 6. Dose-response of the sample count (0.33/0.5 menu, f1+f2 pooled, n=1872)

| row | n samples | wins vs champ (1566.5) | dW | d c/h | t | clock ratio |
|---|---|---|---|---|---|---|
| z_s2 | 600 | 1687.0 | +120.5 | +0.171 | +5.40 | 1.102 |
| f_n45 | 450 | 1652.0 | +85.5 | +0.098 | +2.79 | 0.965 |
| f_n30 | 300 | 1620.0 | +53.5 | −0.016 | −0.45 | 0.840 |

Fewer samples lose wins and chips in a monotonic way. Each 150 samples cost about 33 wins per 1872 and save about 0.13 of the clock ratio. At Stage 1 (f1s) the order of z_s2 and f_n45 is reversed (+66 vs +77).

## 7. Stress, review, rules

- [REVIEW-P1.md](REVIEW-P1.md): p1_ps/p1_dk/p1_bm diffs contain only their build strings, with no bugs and two minor risks. Cut stress set: 24/24 wins each, 0 forfeits, 0 notices, max 23.7 s (S2, 2 legs).
- [REVIEW-FINAL.md](REVIEW-FINAL.md) Part A: the diffs of z_s2, z_v2, f_c1, f_v2b and f_n45 touch only the P profile and the `sizes` line, with no new import, print or file write. The flagged risk: 0.33 and 0.5 share fold bucket 0, a prior seeded for 0.4. Start-up: all 5 finalists and the champion have max 0.78-0.98 s, under the 1.5 s rule.
- Stress (cut set): z_s2, z_v2, f_c1 and f_n45 each won 24/24 with 0 forfeits, 0 notices and 0 unparsed. Max Stage 2 times were 21.1, 39.3, 34.1 and 36.2 s, against a 75 s bank per leg. **f_v2b and f_n30 have no stress line in REVIEW-FINAL.** Outsiders (seed 4242, organiser engine): z_s2 won 8/9 (lost to x_gto by 435), f_c1 won 9/9. Max time was 41 s (x_edge).
- Stress (cut set, `stress/stress_<name>.log` SUMMARY lines; 24 matches each, max time S1 / S2 in s):

| bot | wins | forfeits | notices | unparsed | max S1 | max S2 |
|---|---|---|---|---|---|---|
| f_n45 | 24/24 | 0 | 0 | 0 | 15.13 | 36.23 |
| f_n52 | 24/24 | 0 | 0 | 0 | 15.01 | 24.69 |
| f_n56 | 24/24 | 0 | 0 | 0 | 9.19 | 24.52 |
| g_t2 | 24/24 | 0 | 0 | 0 | 15.83 | 29.33 |
| g_t3 | 24/24 | 0 | 0 | 0 | 15.26 | 28.06 |
| g_t4 | 24/24 | 0 | 0 | 0 | 16.35 | 28.10 |
| g_t6 | 24/24 | 0 | 0 | 0 | 14.97 | 29.53 |
| g_v7 | 24/24 | 0 | 0 | 0 | 14.97 | 25.82 |
| g_w3 | 24/24 | 0 | 0 | 0 | 14.70 | 26.32 |

- [RULES-NOTES.md](RULES-NOTES.md): the prize is Stage 2 match wins (R7.6-8.2). The tie-break caps chips at ±C (R8.3). One forfeit = a loss at −C (R9.1-9.2). No state may be carried between legs (R5.9, 10.3). The ZIP must contain own code only (R10.1).

## FINAL PICK

**New champion: `f_n45`** ([f_n45/bot.py](f_n45/bot.py), SHA256 `e4c9dbbe07a64c90e21ff031067da5b3721c71ba251cefcadef5f6a7ba41c859`, 33490 bytes).
Change vs the old champion `fable5_b_fast`: flop/turn bet-and-raise menu `sz=(0.33, 0.5)` instead of `(0.4, 0.8)`, and `n=450` samples instead of 600. Nothing else (REVIEW-FINAL Part A).

| run (spec `a4-push-<run>-h*`) | stage | n | f_n45 wins | old champ wins | dW | p | clock | maxT | forfeits | notices |
|---|---|---|---|---|---|---|---|---|---|---|
| f1 | 2 | 936 | 826.0 | 779.0 | +47.0 | 0.000 | 0.954 | 21.3 | 0 | 0 |
| f2 | 2 | 936 | 826.0 | 787.5 | +38.5 | 0.002 | 0.976 | 16.0 | 0 | 0 |
| f3w (wider field) | 2 | 204 | 193.0 | 184.0 | +9.0 | 0.049 | 0.985 | 15.7 | 0 | 0 |
| f4 | 2 | 702 | 637.0 | 591.0 | +46.0 | 0.000 | 0.933 | 18.4 | 0 | 0 |
| f5 | 2 | 702 | 614.0 | 577.0 | +37.0 | 0.001 | 0.977 | 17.4 | 0 | 0 |
| **pooled S2** f1+f2+f3w+f4+f5 | 2 | 3480 | 3096.0 | 2918.5 | **+177.5** | 0.000 | 0.962 | 21.3 | 0 | 0 |
| f1s | 1 | 936 | 777.0 | 700.0 | +77.0 | 0.000 | 1.022 | 7.4 | 0 | 0 |
| f4s | 1 | 702 | 567.0 | 534.0 | +33.0 | 0.007 | 0.979 | 6.5 | 0 | 0 |
| **pooled S1** f1s+f4s | 1 | 1638 | 1344.0 | 1234.0 | **+110.0** | 0.000 | 1.003 | 7.4 | 0 | 0 |

Stress: 24/24, 0 forfeits, 0 notices, 0 unparsed, max 36.23 s at Stage 2 (75 s bank). Review: [REVIEW-FINAL.md](REVIEW-FINAL.md) (no failures; risk = 0.33 and 0.5 share fold bucket 0). Start-up max 0.781 s.

Reasons:
1. Every small-menu bot beat the old champion on Stage 2 match wins in every fresh-deal run: f1, f2, f3w (section 5), f4 (+29.0 to +56.0), f5 (+31.0 to +43.0), f5a (+24.0 to +43.5); 0 forfeits, 0 notices.
2. f_n45 has the most evidence of any eligible bot: five fresh Stage 2 runs (f1, f2, f3w, f4, f5; pooled +177.5 of 3480, p 0.000) and two Stage 1 runs (f1s, f4s; pooled +110.0 of 1638), all ahead of the old champion.
3. Clock gate (mean lab clock ≤ ×1.05 of the old champion on the same deals, both stages): f_n45 passes (S2 pooled 0.962, S1 pooled 1.003). z_s2 (600 samples) fails at both (S2 1.095, S1 1.135). f_n56 fails at Stage 1 (f4s 1.054) and in f5 (1.060). f_n52 passes at Stage 2 (f4+f5+f5a 1.024) but is over at Stage 1 when f4s and f5a1 are pooled (**1.057**, n=1210). The eligible sample counts are level on match wins within noise in f4+f5 (n=1404: f_n45 +83.0, f_n52 +87.0, f_n56 +91.0), so the one with margin on the gate and the most evidence is picked.
4. Still-smaller menus (f5a S2, f5a1 S1, vs f_n52 on the same deals): none clearly beats 0.33/0.5 (best dW +9.5, p 0.328; all p ≥ 0.215). The single-size menus g_t4 (0.33) and g_t3 (0.25) lose chips (t −4.37 / −5.58 at S2, −3.56 / −5.83 at S1) and exceed the gate vs the old champion (S2 1.090 / 1.079, S1 1.132 / 1.164). g_v7 (+ finer river menu) is +8.0 in f5a but −6.5 in f5a1, so it fails the two-run rule.
5. Caveats: the gain comes mostly from our own bot families and the small-bet punishers (f1+f2: family +34.5, c32fam +33.0, punish +14.0 wins); against the outsider group match wins are flat and chips down (+3.0 wins, −0.365 c/h, t −4.54, section 5). Stage 1 is better, not worse (pooled +110.0).

Final ZIP: `final/FINAL_f_n45.zip` (10255 bytes, one entry `bot.py`, SHA256 `5c9a6e9bef5e390f880c04c9d94374e045b10c1ed8989d85c073cba1e2466f71`). `tools/make_final_zip.py` (bot Python 3.11) ended with VERIFY PASS, log [final/FINAL_f_n45.verify.txt](final/FINAL_f_n45.verify.txt); its engine-match time numbers are unreliable (PC busy). Independent `zipfile` check: entries `['bot.py']`, entry SHA256 = bot SHA256 above.
