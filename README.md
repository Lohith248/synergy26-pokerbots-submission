# Synergy'26 Pokerbots: our Discard Hold'em bot

This repository holds our final bot for the Synergy'26 Pokerbots competition, how it works, and how we chose it. It also includes the match data and scripts needed to check every number below.

| | |
|---|---|
| Uploaded file | [`submission/bot.zip`](submission/bot.zip): one entry, `bot.py`, 10.3 KB |
| Bot source | [`bot.py`](bot.py), one file, Python 3.11, standard library + numpy |
| `bot.py` SHA256 | `7bfe5231831fe29e7585fb3fa7608799d82e03653204b44d1da6554b0cef3da8` |
| `bot.zip` SHA256 | `b3eb2f4228f3b0cad807984f895f29292dd8d0939e7f2463607b12dfe783c252` |
| Upload check | [`submission/verify-log.txt`](submission/verify-log.txt): ends `VERIFY PASS` |

## 1. The bot in one paragraph

Every time the bot must act, it asks one question: **which legal action wins the most chips on average, given what this opponent has probably got?**

To answer it, the bot:
- estimates how often its hand wins against each hand the opponent could hold;
- weights those hands by what the opponent's betting and exposed discard say about them;
- predicts how often this opponent folds, calls or raises, from rates it learns during the match;
- compares the expected chips of fold, check, call and each raise size, and plays the best one.

Nothing is hard-coded per opponent and no information is carried between legs or matches.

## 2. How it works

**Hand strength (Monte Carlo and enumeration).**
- Before the discard, the bot samples 450 possible opponent 3-card hands and run-outs. For each sample it scores all three ways of keeping two cards.
- After the discard, both discards are visible. The bot enumerates every 2-card hand the opponent can still hold, and on the turn every river card too.
- Hands are scored by a fast table-based 5-to-7-card evaluator built at start-up (under 1 s).

**The discard.** The bot keeps the two cards with the best win rate against the opponent's likely range. When the range is too narrow to trust, it uses the plain average instead.

**Reading the opponent.** The opponent's possible hands are weighted by:
- what the opponent did on each street (bet, check, call or raise);
- the card the opponent threw away.

The weights use the opponent's own measured rates, so a player who bets everything is read differently from one who bets only strong hands.

**Learning during a leg.** After every hand, the bot updates simple counts with a prior, so early hands do not swing them:
- how often the opponent folds to a bet, by street and bet size;
- how often it folds to a raise and to an all-in;
- how often it bets, stabs after a check, raises, 3-bets and 4-bets.

At showdown it also records whether the opponent's river or turn aggression was a bluff, and whether a river check hid a strong hand.

**Choosing the action.** The bot computes the expected chips of each option:
- **Fold** is 0.
- **Call** is the win rate times the pot, minus the cost of calling, minus a small safety margin.
- **Check** credits the chance that the opponent bets into us afterwards.
- **Each raise size** counts the chips we take when the opponent folds, plus our share of the bigger pot when it continues with its calling range.
- **Preflop raises** also account for the opponent's chance of re-raising.

**Bluffs** are allowed only when the numbers say the fold equity pays. They are mixed randomly, so the bot is not predictable.

**Bet sizes.**

| Street | Sizes (fraction of the pot) |
|---|---|
| Preflop | 1.0 |
| Flop and turn | 0.33 and 0.5 (the final change, see section 4) |
| River | 0.4, 0.8 and 1.2 |

Raises close to all-in become all-in.

**Never losing on time or errors.** A forfeit loses the whole match, so safety comes first:
- The bot measures its own cost per hand and per reply and compares it with the time bank it has left. It switches to fewer samples, then to a no-simulation emergency mode, before the bank gets tight; 15% of the bank is never planned for.
- Every request is wrapped: any error falls back to a legal action.
- It prints only protocol replies, writes no files and exits on `match_end`.

## 3. How we developed it

1. **Two designs, written from the rules.** Our first bot (candidate1, 6 Nov) used a keep score, sampled equities and a preflop table. On 12 Nov we wrote a second design, "nova", directly from the problem statement and protocol specification. Nova beat the first line in our lab, so the final bot descends from it. Every version is in [`history/`](history/README.md), with its real file date.
2. **A large test field.** We collected over 120 opponents:
    - our own earlier bots and variants;
    - simple styles (calling station, maniac, rock, jam-or-fold, min-bet pest, slow-player);
    - "punisher" bots written to attack a fixed strategy;
    - shifted copies of strong bots.

    This guards against tuning to one opponent.
3. **Duplicate, paired testing on a 6-machine lab (112 cores).** Every match is played like the real tournament: two legs, cards swapped, fresh processes, Stage 1 and Stage 2 lengths. Each candidate plays the **same opponents on the same deals** as the current champion. The comparison is therefore paired, which removes most card luck.
4. **The metric is match wins, as in the rulebook.** Stage 2 standings decide the prizes, so a challenger had to win more Stage 2 matches than the champion on fresh deals, over at least two independent runs. Chips per hand were used only as a screen.
5. **Safety gates for any challenger:**
    - 0 forfeits and 0 engine notices;
    - a stress set of 24 matches;
    - start-up under 1.5 s;
    - average time at most 1.05 times the champion's;
    - Stage 1 not clearly worse;
    - a code review of the diff.

From 6 to 15 November we built and tested dozens of bot versions; on the final day alone we tested over 100 variants in about 120,000 two-leg lab matches.

## 4. What we tried and what won

| Idea tested on the final day | Result |
|---|---|
| Position-split opponent model, bet-scaled call margin, keep model learned from showdowns, raise-back pricing | Within noise of the champion (for example +16 and −1 wins in 1,250 matches) |
| 53 single-parameter changes (bluff rate, call margin, priors, induce strength and others) | Only the **bet-size menu** gave a clear, repeatable gain |
| Smaller flop/turn sizes: 0.33/0.5 pot instead of 0.4/0.8 | **+168.5 match wins in 3,276 Stage 2 matches, ahead in every run** |
| Single sizes (0.33 or 0.25), extra-small sizes (0.15/0.33), finer river menu | Not clearly better than 0.33/0.5. The single sizes lost chips and used more time. |
| Sample count 600 / 525 / 450 / 300 | More samples win slightly more but cost time. 450 is the most samples that stays inside the time gate at both stages. |

**Final choice:** the previous champion with flop/turn bets of 0.33/0.5 pot and 450 samples. Only those values and the header comment changed ([`reproduce/build.py`](reproduce/build.py) proves this byte for byte).

## 5. Results of the final bot

All results come from paired matches against the previous champion on the same opponents and the same fresh deals, with 39 opponents, plus 34 different ones in the "wider field" run. A win counts 1 and a draw 0.5.

| Run | Stage | Matches | Final bot wins | Previous champion wins | Gain | Forfeits | Time vs champion |
|---|---|---|---|---|---|---|---|
| f1, f2, f4, f5 (main field) | 2 | 3,276 | 2,903.0 | 2,734.5 | **+168.5** | 0 | ×0.96 |
| f3w (wider field, new opponents) | 2 | 204 | 193.0 | 184.0 | +9.0 | 0 | ×0.99 |
| f6ns (engine without our test shim) | 2 | 429 | 384.0 | 369.0 | +15.0 | 0 | ×0.96 |
| f1s, f4s | 1 | 1,638 | 1,344.0 | 1,234.0 | **+110.0** | 0 | ×1.00 |

**Significance.** Of the Stage 2 matches where only one of the two bots won, the final bot won 351 and the old champion 182 (sign test p < 0.001).

**Safety.**
- 0 forfeits and 0 engine notices across all final runs.
- Stress set: 24 of 24 matches won.
- Slowest Stage 2 match: 36 s for both legs on a loaded PC, against a 75 s bank per leg.
- Start-up: under 0.8 s.

**Honest caveat.** Most of the gain comes against strong adaptive bots (our own families) and bots built to punish small bets. Against very simple outsider styles, the old champion already won nearly every match. There the new bot wins the same number of matches, with slightly fewer chips.

## 6. Rules compliance

| Rule | How the bot meets it |
|---|---|
| R5.10 | One `bot.py`; the ZIP holds only that file at the top level and is under 5 MB. |
| Resource and conduct rules | Standard library + numpy only; no network, files, threads or subprocesses. |
| R5.9, R10.3 | No state between legs or matches. No attempt to recognise duplicate deals. |
| R10.1 | All bot code is our own team's work, written from the organiser documents. |
| R9.1 | Time-bank control plus a legal fallback on any error. |

## 7. Reproduce and check

From the repository root:

```bash
# 1. The submitted bot is the previous champion plus the documented changes (prints MATCH)
python reproduce/build.py

# 2. The result tables above, recomputed from the raw match records
cd evaluation
python fintab.py fable5_b_fast "S2=results/f[1245].jsonl" "wide=results/f3w.jsonl" "noshim=results/f6ns.jsonl" "S1=results/f[14]s.jsonl"
python pairtab.py fable5_b_fast results/f1.jsonl results/f2.jsonl --groups groups.json   # results by opponent group
```

To play the bot yourself, use the organiser starter kit (not included here; it belongs to the organisers):

```bash
python engine.py --stage 2 --seed 1 path/to/bot.py bot.py
```

Run this from the `Starter_Kit` folder. The engine's own `bot.py` is the starter bot.

Each line of `evaluation/results/*.jsonl` is one complete two-leg match. It records:
- both bots and their SHA prefixes;
- the stage and the deal seed;
- our net chips and match points;
- time used, notices and forfeit.

## 8. Repository layout

```
bot.py                     final bot (same file as inside submission/bot.zip)
submission/bot.zip         the uploaded file
submission/verify-log.txt  ZIP check: contents, SHA256, matches under the organiser engine on Python 3.11
reproduce/                 previous champion + build.py that rebuilds bot.py exactly
evaluation/                scripts that compute the tables + raw records of the final-day runs
docs/full-lab-log.md       complete evidence log of the final day (every run and candidate)
docs/code-review.md        independent review of the final changes and stress results
history/                   earlier versions of the bot, 6-14 Nov, with their real file dates
```
