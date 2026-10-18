# Subgroup intervals

Subgroups report intervals only; no conclusions are drawn. Under pure chance, about 5% of intervals exclude 0.

S = source only; C0 = source plus CBE documents; C = C0 plus find/query; W = source plus CodeWiki documents. Differences are score points, left arm minus right arm. All intervals are recorded 95% percentile bootstrap intervals over paired questions (10,000 resamples). This renderer copies recorded means and endpoints; it does not recompute bootstrap samples. Zero at either endpoint counts as containing 0. Values are displayed to two decimals; the zero test uses the unrounded endpoints.

## E2: question types and layers, 10 steps

Subgroups report intervals only; no conclusions are drawn. Under pure chance, about 5% of intervals exclude 0.

Source: `e2-flask/metrics.json`, `categories`.

The layer-1 subgroup has one question: its five point intervals are included for completeness but cannot express uncertainty. The README count excludes those five rows.

| Subgroup | Score | Comparison | n | Mean difference | 95% interval | Contains 0? |
|---|---|---|---:|---:|---|---|
| swe_type:What | five-dimension | C-S | 12 | +3.75 | [-1.08, +10.42] | yes |
| swe_type:What | five-dimension | C0-S | 12 | -2.17 | [-9.42, +6.42] | yes |
| swe_type:What | five-dimension | C-C0 | 12 | +5.92 | [+0.75, +11.00] | no |
| swe_type:What | five-dimension | C0-W | 12 | -1.75 | [-7.33, +3.67] | yes |
| swe_type:What | five-dimension | C-W | 12 | +4.17 | [-4.33, +12.92] | yes |
| swe_type:How | five-dimension | C-S | 12 | -1.67 | [-4.58, +1.00] | yes |
| swe_type:How | five-dimension | C0-S | 12 | +0.83 | [-2.75, +5.17] | yes |
| swe_type:How | five-dimension | C-C0 | 12 | -2.50 | [-6.92, +1.67] | yes |
| swe_type:How | five-dimension | C0-W | 12 | +2.67 | [-0.50, +5.67] | yes |
| swe_type:How | five-dimension | C-W | 12 | +0.17 | [-2.25, +2.58] | yes |
| swe_type:Why | five-dimension | C-S | 12 | -4.17 | [-10.59, +0.58] | yes |
| swe_type:Why | five-dimension | C0-S | 12 | -0.50 | [-3.08, +2.83] | yes |
| swe_type:Why | five-dimension | C-C0 | 12 | -3.67 | [-10.50, +2.00] | yes |
| swe_type:Why | five-dimension | C0-W | 12 | +5.25 | [-0.42, +12.42] | yes |
| swe_type:Why | five-dimension | C-W | 12 | +1.58 | [-4.25, +8.92] | yes |
| swe_type:Where | five-dimension | C-S | 12 | +0.25 | [-4.42, +4.92] | yes |
| swe_type:Where | five-dimension | C0-S | 12 | +2.58 | [-3.33, +8.83] | yes |
| swe_type:Where | five-dimension | C-C0 | 12 | -2.33 | [-6.50, +1.83] | yes |
| swe_type:Where | five-dimension | C0-W | 12 | +3.92 | [-1.00, +9.33] | yes |
| swe_type:Where | five-dimension | C-W | 12 | +1.58 | [-3.58, +7.00] | yes |
| layer:1 (degenerate) | five-dimension | C-S | 1 | -4.00 | [-4.00, -4.00] | no |
| layer:1 (degenerate) | five-dimension | C0-S | 1 | -1.00 | [-1.00, -1.00] | no |
| layer:1 (degenerate) | five-dimension | C-C0 | 1 | -3.00 | [-3.00, -3.00] | no |
| layer:1 (degenerate) | five-dimension | C0-W | 1 | +12.00 | [+12.00, +12.00] | no |
| layer:1 (degenerate) | five-dimension | C-W | 1 | +9.00 | [+9.00, +9.00] | no |
| layer:2 | five-dimension | C-S | 13 | -1.31 | [-3.92, +1.15] | yes |
| layer:2 | five-dimension | C0-S | 13 | +1.38 | [-1.23, +5.15] | yes |
| layer:2 | five-dimension | C-C0 | 13 | -2.69 | [-6.62, +0.69] | yes |
| layer:2 | five-dimension | C0-W | 13 | +2.38 | [-0.54, +5.15] | yes |
| layer:2 | five-dimension | C-W | 13 | -0.31 | [-2.62, +1.92] | yes |
| layer:3 | five-dimension | C-S | 17 | +2.29 | [-2.47, +8.06] | yes |
| layer:3 | five-dimension | C0-S | 17 | +1.18 | [-4.94, +8.30] | yes |
| layer:3 | five-dimension | C-C0 | 17 | +1.12 | [-3.00, +5.29] | yes |
| layer:3 | five-dimension | C0-W | 17 | +0.71 | [-4.18, +5.53] | yes |
| layer:3 | five-dimension | C-W | 17 | +1.82 | [-3.12, +6.88] | yes |
| layer:4 | five-dimension | C-S | 17 | -2.35 | [-7.35, +1.47] | yes |
| layer:4 | five-dimension | C0-S | 17 | -1.65 | [-5.41, +1.88] | yes |
| layer:4 | five-dimension | C-C0 | 17 | -0.71 | [-6.88, +5.00] | yes |
| layer:4 | five-dimension | C0-W | 17 | +3.88 | [-0.82, +9.65] | yes |
| layer:4 | five-dimension | C-W | 17 | +3.18 | [-3.12, +10.12] | yes |

Recorded rows: 40; intervals excluding 0: 6.

## E2: difficulty bands, 10 steps

Subgroups report intervals only; no conclusions are drawn. Under pure chance, about 5% of intervals exclude 0.

Source: `e2-flask/metrics.json`, `difficulty_calibration.strata`.

The median split is 68.5; the alternative threshold is 80. High means direct-answer score >= threshold. These describe difficulty under the short direct-answer prompt and its judge. Only C-S intervals are stored for these bands. E2b records one-question threshold-80/high as a degenerate point interval. No question-type or layer interval table is stored in E2b metrics.

| Subgroup | Score | Comparison | n | Mean difference | 95% interval | Contains 0? |
|---|---|---|---:|---:|---|---|
| median, threshold 68.5, high | five-dimension | C-S | 24 | -3.17 | [-6.96, -0.08] | no |
| median, threshold 68.5, low | five-dimension | C-S | 24 | +2.25 | [-0.96, +6.21] | yes |
| threshold80, threshold 80, high | five-dimension | C-S | 7 | +0.43 | [-2.29, +2.43] | yes |
| threshold80, threshold 80, low | five-dimension | C-S | 41 | -0.61 | [-3.61, +2.29] | yes |

Recorded rows: 4; intervals excluding 0: 1.

## E2b: difficulty bands, 25 steps

Subgroups report intervals only; no conclusions are drawn. Under pure chance, about 5% of intervals exclude 0.

Source: `e2b-flask-25steps/metrics.json`, `difficulty_calibration.strata`.

The median split is 68.5; the alternative threshold is 80. High means direct-answer score >= threshold. These describe difficulty under the short direct-answer prompt and its judge. Only C-S intervals are stored for these bands. E2b records one-question threshold-80/high as a degenerate point interval. No question-type or layer interval table is stored in E2b metrics.

| Subgroup | Score | Comparison | n | Mean difference | 95% interval | Contains 0? |
|---|---|---|---:|---:|---|---|
| median, threshold 68.5, high | five-dimension | C-S | 12 | -1.92 | [-6.58, +4.17] | yes |
| median, threshold 68.5, low | five-dimension | C-S | 12 | +5.67 | [-1.00, +13.75] | yes |
| threshold80, threshold 80, high (degenerate) | five-dimension | C-S | 1 | -6.00 | [-6.00, -6.00] | no |
| threshold80, threshold 80, low | five-dimension | C-S | 23 | +2.22 | [-2.39, +7.70] | yes |

Recorded rows: 4; intervals excluding 0: 1.

## E3: question types and layers, 10 steps

Subgroups report intervals only; no conclusions are drawn. Under pure chance, about 5% of intervals exclude 0.

Source: `e3-pytest/metrics.json`, `categories`.

| Subgroup | Score | Comparison | n | Mean difference | 95% interval | Contains 0? |
|---|---|---|---:|---:|---|---|
| swe_type:What | five-dimension | C-S | 12 | +0.08 | [-3.92, +4.08] | yes |
| swe_type:What | five-dimension | C0-S | 12 | +2.08 | [-0.42, +4.83] | yes |
| swe_type:What | five-dimension | C-C0 | 12 | -2.00 | [-5.50, +1.08] | yes |
| swe_type:How | five-dimension | C-S | 12 | +4.50 | [-2.58, +13.42] | yes |
| swe_type:How | five-dimension | C0-S | 12 | +1.58 | [-3.58, +7.25] | yes |
| swe_type:How | five-dimension | C-C0 | 12 | +2.92 | [-2.58, +11.08] | yes |
| swe_type:Why | five-dimension | C-S | 12 | -5.92 | [-13.08, -0.17] | no |
| swe_type:Why | five-dimension | C0-S | 12 | +0.00 | [-4.42, +3.67] | yes |
| swe_type:Why | five-dimension | C-C0 | 12 | -5.92 | [-12.50, -1.00] | no |
| swe_type:Where | five-dimension | C-S | 12 | +1.08 | [-2.50, +5.17] | yes |
| swe_type:Where | five-dimension | C0-S | 12 | +1.17 | [-3.92, +6.92] | yes |
| swe_type:Where | five-dimension | C-C0 | 12 | -0.08 | [-3.33, +2.92] | yes |
| layer:1 | five-dimension | C-S | 4 | +0.00 | [-4.50, +3.50] | yes |
| layer:1 | five-dimension | C0-S | 4 | +1.50 | [-4.50, +6.50] | yes |
| layer:1 | five-dimension | C-C0 | 4 | -1.50 | [-3.00, +0.00] | yes |
| layer:2 | five-dimension | C-S | 14 | -1.36 | [-8.43, +4.93] | yes |
| layer:2 | five-dimension | C0-S | 14 | +3.07 | [-0.86, +7.79] | yes |
| layer:2 | five-dimension | C-C0 | 14 | -4.43 | [-10.64, +0.14] | yes |
| layer:3 | five-dimension | C-S | 12 | +0.00 | [-3.92, +4.33] | yes |
| layer:3 | five-dimension | C0-S | 12 | -1.75 | [-6.42, +3.50] | yes |
| layer:3 | five-dimension | C-C0 | 12 | +1.75 | [-0.83, +4.25] | yes |
| layer:4 | five-dimension | C-S | 18 | +0.89 | [-4.33, +7.33] | yes |
| layer:4 | five-dimension | C0-S | 18 | +1.67 | [-1.78, +4.94] | yes |
| layer:4 | five-dimension | C-C0 | 18 | -0.78 | [-5.17, +5.22] | yes |

Recorded rows: 24; intervals excluding 0: 2.

## E5: all frozen subgroups, 10 steps

Subgroups report intervals only; no conclusions are drawn. Under pure chance, about 5% of intervals exclude 0.

Source: `e5-curl/metrics.json`, `categories`.

Both rubric and five-dimension scores are shown. `in_docs` is the frozen catalog-presence label; see LABELS.md. Seed 20261018; 10,000 resamples. These 96 rows are the denominator used in the README.

| Subgroup | Score | Comparison | n | Mean difference | 95% interval | Contains 0? |
|---|---|---|---:|---:|---|---|
| label_layer:1 | rubric | C-S | 3 | +16.67 | [+0.00, +25.00] | yes |
| label_layer:1 | rubric | C0-S | 3 | +19.44 | [+8.33, +33.33] | no |
| label_layer:1 | rubric | C-C0 | 3 | -2.78 | [-16.67, +16.67] | yes |
| label_layer:1 | five | C-S | 3 | +5.67 | [-2.00, +10.00] | yes |
| label_layer:1 | five | C0-S | 3 | +3.00 | [-5.00, +7.00] | yes |
| label_layer:1 | five | C-C0 | 3 | +2.67 | [+2.00, +3.00] | no |
| label_layer:2 | rubric | C-S | 8 | +1.64 | [-4.55, +8.33] | yes |
| label_layer:2 | rubric | C0-S | 8 | +7.84 | [-4.11, +19.90] | yes |
| label_layer:2 | rubric | C-C0 | 8 | -6.20 | [-14.60, +1.06] | yes |
| label_layer:2 | five | C-S | 8 | +3.75 | [+0.75, +7.62] | no |
| label_layer:2 | five | C0-S | 8 | +1.50 | [-4.25, +7.25] | yes |
| label_layer:2 | five | C-C0 | 8 | +2.25 | [-3.12, +6.62] | yes |
| label_layer:3 | rubric | C-S | 18 | +3.74 | [-2.81, +11.41] | yes |
| label_layer:3 | rubric | C0-S | 18 | +7.90 | [+0.90, +15.51] | no |
| label_layer:3 | rubric | C-C0 | 18 | -4.15 | [-13.86, +5.46] | yes |
| label_layer:3 | five | C-S | 18 | -4.72 | [-13.17, +3.22] | yes |
| label_layer:3 | five | C0-S | 18 | +1.83 | [-2.39, +6.33] | yes |
| label_layer:3 | five | C-C0 | 18 | -6.56 | [-14.67, +1.00] | yes |
| label_layer:4 | rubric | C-S | 11 | +8.50 | [-2.23, +20.52] | yes |
| label_layer:4 | rubric | C0-S | 11 | +0.24 | [-9.10, +8.60] | yes |
| label_layer:4 | rubric | C-C0 | 11 | +8.26 | [-3.03, +22.04] | yes |
| label_layer:4 | five | C-S | 11 | +0.09 | [-7.00, +8.27] | yes |
| label_layer:4 | five | C0-S | 11 | -3.00 | [-9.55, +4.36] | yes |
| label_layer:4 | five | C-C0 | 11 | +3.09 | [-6.09, +12.64] | yes |
| label_swe_type:What | rubric | C-S | 10 | +10.71 | [+1.67, +21.31] | no |
| label_swe_type:What | rubric | C0-S | 10 | +4.52 | [-7.65, +15.99] | yes |
| label_swe_type:What | rubric | C-C0 | 10 | +6.19 | [-7.62, +21.77] | yes |
| label_swe_type:What | five | C-S | 10 | +5.10 | [+0.50, +12.50] | no |
| label_swe_type:What | five | C0-S | 10 | +2.30 | [-2.70, +7.20] | yes |
| label_swe_type:What | five | C-C0 | 10 | +2.80 | [-2.50, +8.20] | yes |
| label_swe_type:How | rubric | C-S | 10 | -0.06 | [-6.36, +6.83] | yes |
| label_swe_type:How | rubric | C0-S | 10 | +6.50 | [-2.30, +16.84] | yes |
| label_swe_type:How | rubric | C-C0 | 10 | -6.56 | [-17.45, +2.47] | yes |
| label_swe_type:How | five | C-S | 10 | -2.10 | [-10.80, +5.50] | yes |
| label_swe_type:How | five | C0-S | 10 | +1.10 | [-4.20, +7.30] | yes |
| label_swe_type:How | five | C-C0 | 10 | -3.20 | [-12.70, +4.90] | yes |
| label_swe_type:Why | rubric | C-S | 10 | +7.53 | [-4.11, +20.55] | yes |
| label_swe_type:Why | rubric | C0-S | 10 | +3.90 | [-1.54, +11.00] | yes |
| label_swe_type:Why | rubric | C-C0 | 10 | +3.64 | [-5.00, +14.40] | yes |
| label_swe_type:Why | five | C-S | 10 | +0.20 | [-7.60, +9.10] | yes |
| label_swe_type:Why | five | C0-S | 10 | -2.10 | [-9.10, +5.90] | yes |
| label_swe_type:Why | five | C-C0 | 10 | +2.30 | [-7.60, +12.50] | yes |
| label_swe_type:Where | rubric | C-S | 10 | +4.22 | [-3.89, +12.89] | yes |
| label_swe_type:Where | rubric | C0-S | 10 | +11.67 | [+0.39, +22.33] | no |
| label_swe_type:Where | rubric | C-C0 | 10 | -7.44 | [-18.89, +3.50] | yes |
| label_swe_type:Where | five | C-S | 10 | -6.90 | [-18.80, +2.00] | yes |
| label_swe_type:Where | five | C0-S | 10 | +0.80 | [-5.20, +7.30] | yes |
| label_swe_type:Where | five | C-C0 | 10 | -7.70 | [-19.30, +1.80] | yes |
| layer:1+2 | rubric | C-S | 11 | +5.74 | [-1.03, +13.13] | yes |
| layer:1+2 | rubric | C0-S | 11 | +11.00 | [+1.11, +20.74] | no |
| layer:1+2 | rubric | C-C0 | 11 | -5.26 | [-12.58, +1.77] | yes |
| layer:1+2 | five | C-S | 11 | +4.27 | [+1.36, +7.55] | no |
| layer:1+2 | five | C0-S | 11 | +1.91 | [-2.64, +6.27] | yes |
| layer:1+2 | five | C-C0 | 11 | +2.36 | [-1.45, +5.55] | yes |
| layer:3+4 | rubric | C-S | 29 | +5.55 | [-0.29, +12.20] | yes |
| layer:3+4 | rubric | C0-S | 29 | +4.99 | [-0.80, +10.81] | yes |
| layer:3+4 | rubric | C-C0 | 29 | +0.56 | [-7.14, +8.80] | yes |
| layer:3+4 | five | C-S | 29 | -2.90 | [-8.93, +2.83] | yes |
| layer:3+4 | five | C0-S | 29 | +0.00 | [-3.83, +3.93] | yes |
| layer:3+4 | five | C-C0 | 29 | -2.90 | [-9.31, +3.38] | yes |
| closed_book:=0 | rubric | C-S | 28 | +6.64 | [+0.34, +13.34] | no |
| closed_book:=0 | rubric | C0-S | 28 | +8.15 | [+1.33, +14.81] | no |
| closed_book:=0 | rubric | C-C0 | 28 | -1.51 | [-9.85, +7.34] | yes |
| closed_book:=0 | five | C-S | 28 | -4.18 | [-9.61, +0.64] | yes |
| closed_book:=0 | five | C0-S | 28 | -0.71 | [-4.54, +3.29] | yes |
| closed_book:=0 | five | C-C0 | 28 | -3.46 | [-9.96, +2.75] | yes |
| closed_book:>0 | rubric | C-S | 12 | +3.18 | [-2.04, +9.52] | yes |
| closed_book:>0 | rubric | C0-S | 12 | +3.13 | [-2.04, +9.52] | yes |
| closed_book:>0 | rubric | C-C0 | 12 | +0.05 | [-4.17, +4.17] | yes |
| closed_book:>0 | five | C-S | 12 | +6.67 | [+0.00, +14.17] | yes |
| closed_book:>0 | five | C0-S | 12 | +3.42 | [-1.00, +8.00] | yes |
| closed_book:>0 | five | C-C0 | 12 | +3.25 | [-1.25, +7.67] | yes |
| dispatch:true | rubric | C-S | 14 | +2.25 | [-4.07, +8.84] | yes |
| dispatch:true | rubric | C0-S | 14 | +3.89 | [-5.20, +13.48] | yes |
| dispatch:true | rubric | C-C0 | 14 | -1.64 | [-12.94, +10.10] | yes |
| dispatch:true | five | C-S | 14 | +0.57 | [-7.86, +9.43] | yes |
| dispatch:true | five | C0-S | 14 | +3.86 | [-1.50, +9.43] | yes |
| dispatch:true | five | C-C0 | 14 | -3.29 | [-12.07, +5.07] | yes |
| dispatch:false | rubric | C-S | 26 | +7.41 | [+1.14, +14.42] | no |
| dispatch:false | rubric | C0-S | 26 | +8.13 | [+2.33, +13.94] | no |
| dispatch:false | rubric | C-C0 | 26 | -0.72 | [-7.73, +6.72] | yes |
| dispatch:false | five | C-S | 26 | -1.73 | [-7.12, +2.92] | yes |
| dispatch:false | five | C0-S | 26 | -1.27 | [-4.88, +2.42] | yes |
| dispatch:false | five | C-C0 | 26 | -0.46 | [-6.27, +4.92] | yes |
| in_docs:true | rubric | C-S | 30 | +3.08 | [-1.50, +8.39] | yes |
| in_docs:true | rubric | C0-S | 30 | +7.21 | [+1.80, +12.92] | no |
| in_docs:true | rubric | C-C0 | 30 | -4.13 | [-10.30, +2.05] | yes |
| in_docs:true | five | C-S | 30 | -3.30 | [-8.27, +1.00] | yes |
| in_docs:true | five | C0-S | 30 | +0.60 | [-2.80, +4.27] | yes |
| in_docs:true | five | C-C0 | 30 | -3.90 | [-9.47, +1.17] | yes |
| in_docs:false | rubric | C-S | 10 | +13.15 | [+1.67, +25.12] | no |
| in_docs:false | rubric | C0-S | 10 | +4.94 | [-7.00, +15.41] | yes |
| in_docs:false | rubric | C-C0 | 10 | +8.21 | [-6.15, +23.86] | yes |
| in_docs:false | five | C-S | 10 | +6.20 | [-3.20, +16.30] | yes |
| in_docs:false | five | C0-S | 10 | +0.30 | [-6.20, +6.80] | yes |
| in_docs:false | five | C-C0 | 10 | +5.90 | [-1.80, +14.90] | yes |

Recorded rows: 96; intervals excluding 0: 15.

## E5: strict own-unit supplement, main-session recomputation

Subgroups report intervals only; no conclusions are drawn. Under pure chance, about 5% of intervals exclude 0.

Source: `e5-curl/spotcheck-and-recompute/recompute.json`, `subgroups.own_unit` and `subgroups.not_own_unit`.

This supplement was recomputed by the main evaluation session, with bootstrap seeds different from the primary E5 metrics. The recompute JSON does not record the seed values. It is additional to the 96 frozen subgroup intervals. In the no-own-unit rubric C0-S interval, the lower endpoint crosses 0 for 10 of 30 seeds (README).

| Subgroup | Score | Comparison | n | Mean difference | 95% interval | Contains 0? |
|---|---|---|---:|---:|---|---|
| own_unit | rubric | C-S | 15 | +7.19 | [+0.40, +15.22] | no |
| own_unit | rubric | C0-S | 15 | +6.36 | [-0.71, +14.02] | yes |
| own_unit | rubric | C-C0 | 15 | +0.83 | [-8.03, +10.05] | yes |
| own_unit | fivedim | C-S | 15 | +2.73 | [-0.47, +6.00] | yes |
| own_unit | fivedim | C0-S | 15 | +1.73 | [-3.47, +7.00] | yes |
| own_unit | fivedim | C-C0 | 15 | +1.00 | [-5.93, +6.33] | yes |
| not_own_unit | rubric | C-S | 25 | +4.65 | [-1.58, +11.39] | yes |
| not_own_unit | rubric | C0-S | 25 | +6.81 | [+0.06, +13.46] | no |
| not_own_unit | rubric | C-C0 | 25 | -2.17 | [-10.11, +6.33] | yes |
| not_own_unit | fivedim | C-S | 25 | -3.12 | [-9.96, +3.52] | yes |
| not_own_unit | fivedim | C0-S | 25 | -0.20 | [-3.88, +3.88] | yes |
| not_own_unit | fivedim | C-C0 | 25 | -2.92 | [-9.68, +3.64] | yes |

Recorded rows: 12; intervals excluding 0: 2.

## Cross-check against the evaluation README

| Set | Rendered excluding 0 / denominator | README | Match? |
|---|---:|---:|---|
| E2 README denominator | 1/35 | 1/35 | yes |
| E3: question types and layers, 10 steps | 2/24 | 2/24 | yes |
| E5: all frozen subgroups, 10 steps | 15/96 | 15/96 | yes |

The difficulty tables, E2 degenerate rows and own-unit supplement are outside those three denominators. The E5 subgroups overlap; a count of intervals excluding 0 is not a multiple-comparison conclusion.

## Regenerate

From the public repository root:

```sh
python evaluation/tools/render_subgroups.py --evaluation evaluation --output evaluation/SUBGROUPS.md
```
