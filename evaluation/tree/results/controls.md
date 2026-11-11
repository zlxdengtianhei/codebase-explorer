# Checks on the scales

## 1. Fewer modules, higher recall (C)

Directory cuts of each repo at every depth, plus one module for everything. Random-3 = expected recall when three modules are picked at random; lift = recall / share. Lift stays near 1 for a random pick at any size; recall alone does not.

| repo | cut | modules | random-3 recall | random-3 share | lift | best-3 recall |
|---|---|---|---|---|---|---|
| ruby_llm | dir depth 0 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| ruby_llm | dir depth 1 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| ruby_llm | dir depth 2 | 4 | 0.75 | 0.76 | 1.00 | 1.00 |
| ruby_llm | dir depth 3 | 7 | 0.43 | 0.43 | 1.00 | 1.00 |
| ruby_llm | dir depth 4 | 22 | 0.14 | 0.14 | 1.00 | 1.00 |
| ruby_llm | dir depth 5 | 23 | 0.13 | 0.13 | 1.00 | 1.00 |
| ruby_llm | one module for everything | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| gson | dir depth 0 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| gson | dir depth 1 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| gson | dir depth 2 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| gson | dir depth 3 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| gson | dir depth 4 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| gson | dir depth 5 | 2 | 1.00 | 1.00 | 1.00 | 1.00 |
| gson | dir depth 6 | 2 | 1.00 | 1.00 | 1.00 | 1.00 |
| gson | dir depth 7 | 2 | 1.00 | 1.00 | 1.00 | 1.00 |
| gson | dir depth 8 | 6 | 0.50 | 0.51 | 0.99 | 1.00 |
| gson | dir depth 9 | 9 | 0.33 | 0.33 | 1.00 | 1.00 |
| gson | dir depth 10 | 10 | 0.30 | 0.30 | 1.01 | 1.00 |
| gson | one module for everything | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| tsdown | dir depth 0 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| tsdown | dir depth 1 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| tsdown | dir depth 2 | 4 | 0.75 | 0.75 | 1.00 | 1.00 |
| tsdown | dir depth 3 | 5 | 0.60 | 0.60 | 0.99 | 1.00 |
| tsdown | one module for everything | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| fmt | dir depth 0 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| fmt | dir depth 1 | 2 | 1.00 | 1.00 | 1.00 | 1.00 |
| fmt | dir depth 2 | 2 | 1.00 | 1.00 | 1.00 | 1.00 |
| fmt | one module for everything | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| flask | dir depth 0 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| flask | dir depth 1 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| flask | dir depth 2 | 1 | 1.00 | 1.00 | 1.00 | 1.00 |
| flask | dir depth 3 | 3 | 1.00 | 1.00 | 1.00 | 1.00 |
| flask | dir depth 4 | 3 | 1.00 | 1.00 | 1.00 | 1.00 |
| flask | dir depth 5 | 3 | 1.00 | 1.00 | 1.00 | 1.00 |
| flask | one module for everything | 1 | 1.00 | 1.00 | 1.00 | 1.00 |

## 2. B reads mostly 'files of one directory stay together' (B2) and has fixed floor and ceiling (B1, B2)

Q values. 'randomly paired' keeps every directory whole but merges directories at random into groups of about two.

| repo | T0 up1: soft Q | T0 up1: hard-majority Q (the probe's way) | one file per module | one module for everything | B1 one module | B1 one unit per module | B1 edge weight (call edges) | leaf dirs: real Q | leaf dirs randomly paired (files kept together), mean Q |
|---|---|---|---|---|---|---|---|---|---|
| ruby_llm | 0.047 | 0.047 | -0.024 | -0.000 | 0.000 | -0.009 | 410.000 | 0.082 | 0.069 |
| gson | 0.039 | 0.039 | -0.040 | 0.000 | 0.000 | -0.009 | 755.000 | 0.139 | 0.127 |
| tsdown | 0.007 | 0.007 | -0.050 | 0.000 | 0.000 | -0.022 | 207.000 | 0.048 | 0.097 |
| fmt | 0.027 | 0.027 | -0.086 | -0.000 | 0.000 | -0.082 | 68.000 | -0.021 | -0.021 |
| flask | -0.092 | -0.096 | -0.113 | 0.000 | 0.000 | -0.016 | 283.000 | 0.037 | 0.037 |

## 3. Capability sentences that name a file of their own module

Count of T0 modules whose title or capability contains the stem (4 or more letters) of one of their own member files.

| repo | one level above leaf | leaf |
|---|---|---|
| ruby_llm | 13/17 | 36/51 |
| gson | 5/8 | 14/23 |
| tsdown | 8/9 | 17/19 |
| fmt | 8/13 | 14/37 |
| flask | 6/9 | 13/32 |

## 4. T0 one-level-above-leaf page with and without the capability sentence (C)

| repo | model | recall with | share with | recall without | share without | lift with | lift without | page tokens with | without |
|---|---|---|---|---|---|---|---|---|---|
| ruby_llm | glm-flash | 0.78 | 0.16 | 0.76 | 0.17 | 4.81 | 4.52 | 1344 | 803 |
| ruby_llm | deepseek-flash | 0.84 | 0.16 | 0.78 | 0.16 | 5.18 | 4.78 | 1344 | 803 |
| gson | glm-flash | 0.78 | 0.53 | 0.82 | 0.52 | 1.47 | 1.58 | 831 | 470 |
| gson | deepseek-flash | 0.63 | 0.46 | 0.75 | 0.53 | 1.39 | 1.40 | 831 | 470 |
| tsdown | glm-flash | 0.83 | 0.52 | 0.80 | 0.48 | 1.60 | 1.68 | 477 | 228 |
| tsdown | deepseek-flash | 0.86 | 0.47 | 0.77 | 0.50 | 1.82 | 1.55 | 477 | 228 |
| fmt | glm-flash | 0.73 | 0.39 | 0.71 | 0.40 | 1.86 | 1.77 | 667 | 260 |
| fmt | deepseek-flash | 0.70 | 0.35 | 0.67 | 0.36 | 2.01 | 1.87 | 667 | 260 |
| flask | glm-flash | 0.72 | 0.40 | 0.78 | 0.37 | 1.81 | 2.11 | 696 | 266 |
| flask | deepseek-flash | 0.76 | 0.41 | 0.75 | 0.40 | 1.87 | 1.88 | 696 | 266 |

## 5. Memory test: file names with no map (repo name and commit text only)

Share of the change (by changed lines) that sits in the three files the model named. Compare with the best-3 module recall of the same repo.

| repo | model | exact-path hit | same-file-name hit | tokens per question |
|---|---|---|---|---|
| ruby_llm | glm-flash | 0.36 | 0.43 | 184 |
| ruby_llm | deepseek-flash | 0.45 | 0.46 | 2194 |
| gson | glm-flash | 0.64 | 0.64 | 231 |
| gson | deepseek-flash | 0.71 | 0.74 | 1303 |
| tsdown | glm-flash | 0.11 | 0.24 | 180 |
| tsdown | deepseek-flash | 0.39 | 0.49 | 2157 |
| fmt | glm-flash | 0.32 | 0.32 | 181 |
| fmt | deepseek-flash | 0.32 | 0.32 | 1013 |
| flask | glm-flash | 0.44 | 0.50 | 169 |
| flask | deepseek-flash | 0.50 | 0.69 | 1947 |

## 6. Same question asked twice (temperature 0 sent)

| repo | model | result |
|---|---|---|
| ruby_llm | glm-flash | 14/30 identical chosen sets; mean recall run 1 0.78, run 2 0.73 |
| ruby_llm | deepseek-flash | 14/30 identical chosen sets; mean recall run 1 0.84, run 2 0.80 |
| gson | glm-flash | 14/30 identical chosen sets; mean recall run 1 0.78, run 2 0.75 |
| gson | deepseek-flash | 16/30 identical chosen sets; mean recall run 1 0.63, run 2 0.75 |
| tsdown | glm-flash | 9/30 identical chosen sets; mean recall run 1 0.83, run 2 0.85 |
| tsdown | deepseek-flash | 20/30 identical chosen sets; mean recall run 1 0.86, run 2 0.88 |
| fmt | glm-flash | 14/30 identical chosen sets; mean recall run 1 0.73, run 2 0.70 |
| fmt | deepseek-flash | 23/30 identical chosen sets; mean recall run 1 0.70, run 2 0.70 |
| flask | glm-flash | 13/30 identical chosen sets; mean recall run 1 0.72, run 2 0.82 |
| flask | deepseek-flash | 16/30 identical chosen sets; mean recall run 1 0.76, run 2 0.75 |
