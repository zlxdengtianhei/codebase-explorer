# Trees side by side

For each repo the target size is the module count of T0 one level above the leaf. Each tree uses the C view (leaf, up1 or top) whose module count is closest to it (ties go to the finer view); T1 uses the directory depth matched to T0's up1; T1f has one module per file. Excess recall = recall minus the recall of picking 3 modules at random on the same page.

## C with `deepseek-flash`

| repo | tree | view | modules | recall | share | excess recall | lift | B1 Q at that level | B2 Q at that level | empty nodes |
|---|---|---|---|---|---|---|---|---|---|---|
| ruby_llm | T0 | up1 | 17 | 0.84 | 0.16 | 0.66 | 5.18 | 0.670 | 0.047 | 8 |
| ruby_llm | T1 | up1 | 22 | 0.94 | 0.31 | 0.80 | 3.01 | 0.665 | 0.088 | 0 |
| ruby_llm | T1f | leaf | 108 | 0.74 | 0.05 | 0.71 | 15.66 | 0.638 | -0.024 | 0 |
| ruby_llm | T2 | up1 | 23 | 0.86 | 0.34 | 0.73 | 2.54 | 0.756 | 0.068 | 0 |
| ruby_llm | T3 | up1 | 12 | 0.91 | 0.30 | 0.66 | 3.03 | 0.824 | 0.131 | 0 |
| ruby_llm | T3m | up1 | 12 | 0.95 | 0.29 | 0.69 | 3.27 | 0.824 | 0.131 | 0 |
| gson | T0 | up1 | 8 | 0.63 | 0.46 | 0.25 | 1.39 | 0.313 | 0.039 | 16 |
| gson | T1 | up1 | 9 | 0.82 | 0.68 | 0.49 | 1.21 | 0.367 | 0.138 | 0 |
| gson | T1f | leaf | 83 | 0.69 | 0.11 | 0.65 | 6.45 | 0.498 | -0.040 | 0 |
| gson | T2 | top | 14 | 0.73 | 0.38 | 0.51 | 1.91 | 0.683 | 0.103 | 0 |
| gson | T3 | top | 7 | 0.90 | 0.69 | 0.48 | 1.31 | 0.660 | 0.080 | 0 |
| gson | T3m | top | 7 | 0.85 | 0.67 | 0.42 | 1.26 | 0.660 | 0.091 | 0 |
| tsdown | T0 | up1 | 9 | 0.86 | 0.47 | 0.52 | 1.82 | 0.282 | 0.007 | 0 |
| tsdown | T1 | up1 | 5 | 0.95 | 0.69 | 0.35 | 1.38 | 0.199 | 0.048 | 0 |
| tsdown | T1f | leaf | 38 | 0.74 | 0.15 | 0.65 | 4.94 | 0.272 | -0.050 | 0 |
| tsdown | T2 | up1 | 9 | 0.75 | 0.55 | 0.41 | 1.37 | 0.498 | -0.008 | 0 |
| tsdown | T3 | up1 | 7 | 0.88 | 0.64 | 0.45 | 1.37 | 0.481 | 0.045 | 0 |
| tsdown | T3m | up1 | 7 | 0.91 | 0.65 | 0.48 | 1.42 | 0.481 | 0.045 | 0 |
| fmt | T0 | up1 | 13 | 0.70 | 0.35 | 0.48 | 2.01 | 0.239 | 0.027 | 0 |
| fmt | T1 | up1 | 2 | 1.00 | 0.99 | 0.00 | 1.01 | -0.000 | -0.021 | 0 |
| fmt | T1f | leaf | 17 | 0.68 | 0.28 | 0.50 | 2.45 | 0.224 | -0.086 | 0 |
| fmt | T2 | up1 | 21 | 0.59 | 0.31 | 0.44 | 1.92 | 0.402 | -0.062 | 0 |
| fmt | T3 | up1 | 8 | 0.65 | 0.40 | 0.28 | 1.64 | 0.544 | -0.025 | 0 |
| fmt | T3m | up1 | 8 | 0.72 | 0.43 | 0.35 | 1.65 | 0.544 | -0.025 | 0 |
| flask | T0 | up1 | 9 | 0.76 | 0.41 | 0.44 | 1.87 | 0.524 | -0.092 | 22 |
| flask | T1 | up1 | 3 | 1.00 | 1.00 | 0.00 | 1.00 | 0.448 | 0.037 | 0 |
| flask | T1f | leaf | 22 | 0.70 | 0.25 | 0.56 | 2.86 | 0.472 | -0.113 | 0 |
| flask | T2 | up1 | 14 | 0.75 | 0.42 | 0.53 | 1.79 | 0.617 | -0.012 | 0 |
| flask | T3 | up1 | 10 | 0.78 | 0.44 | 0.48 | 1.77 | 0.704 | -0.058 | 0 |
| flask | T3m | up1 | 10 | 0.78 | 0.43 | 0.48 | 1.84 | 0.704 | -0.058 | 0 |

## C with `glm-flash`

| repo | tree | view | modules | recall | share | excess recall | lift | B1 Q at that level | B2 Q at that level | empty nodes |
|---|---|---|---|---|---|---|---|---|---|---|
| ruby_llm | T0 | up1 | 17 | 0.78 | 0.16 | 0.61 | 4.81 | 0.670 | 0.047 | 8 |
| ruby_llm | T1 | up1 | 22 | 0.91 | 0.31 | 0.77 | 2.93 | 0.665 | 0.088 | 0 |
| ruby_llm | T1f | leaf | 108 | 0.73 | 0.05 | 0.70 | 15.84 | 0.638 | -0.024 | 0 |
| ruby_llm | T2 | up1 | 23 | 0.81 | 0.34 | 0.68 | 2.36 | 0.756 | 0.068 | 0 |
| ruby_llm | T3 | up1 | 12 | 0.87 | 0.29 | 0.62 | 2.97 | 0.824 | 0.131 | 0 |
| ruby_llm | T3m | up1 | 12 | 0.89 | 0.29 | 0.63 | 3.09 | 0.824 | 0.131 | 0 |
| gson | T0 | up1 | 8 | 0.78 | 0.53 | 0.40 | 1.47 | 0.313 | 0.039 | 16 |
| gson | T1 | up1 | 9 | 0.86 | 0.67 | 0.52 | 1.29 | 0.367 | 0.138 | 0 |
| gson | T1f | leaf | 83 | 0.67 | 0.12 | 0.64 | 5.75 | 0.498 | -0.040 | 0 |
| gson | T2 | top | 14 | 0.71 | 0.43 | 0.49 | 1.65 | 0.683 | 0.103 | 0 |
| gson | T3 | top | 7 | 0.87 | 0.67 | 0.45 | 1.30 | 0.660 | 0.080 | 0 |
| gson | T3m | top | 7 | 0.87 | 0.65 | 0.45 | 1.35 | 0.660 | 0.091 | 0 |
| tsdown | T0 | up1 | 9 | 0.83 | 0.52 | 0.49 | 1.60 | 0.282 | 0.007 | 0 |
| tsdown | T1 | up1 | 5 | 0.90 | 0.66 | 0.30 | 1.36 | 0.199 | 0.048 | 0 |
| tsdown | T1f | leaf | 38 | 0.68 | 0.13 | 0.60 | 5.11 | 0.272 | -0.050 | 0 |
| tsdown | T2 | up1 | 9 | 0.61 | 0.48 | 0.28 | 1.28 | 0.498 | -0.008 | 0 |
| tsdown | T3 | up1 | 7 | 0.90 | 0.61 | 0.47 | 1.48 | 0.481 | 0.045 | 0 |
| tsdown | T3m | up1 | 7 | 0.85 | 0.62 | 0.42 | 1.37 | 0.481 | 0.045 | 0 |
| fmt | T0 | up1 | 13 | 0.73 | 0.39 | 0.50 | 1.86 | 0.239 | 0.027 | 0 |
| fmt | T1 | up1 | 2 | 1.00 | 1.00 | 0.00 | 1.00 | -0.000 | -0.021 | 0 |
| fmt | T1f | leaf | 17 | 0.59 | 0.26 | 0.41 | 2.24 | 0.224 | -0.086 | 0 |
| fmt | T2 | up1 | 21 | 0.73 | 0.33 | 0.58 | 2.19 | 0.402 | -0.062 | 0 |
| fmt | T3 | up1 | 8 | 0.78 | 0.44 | 0.41 | 1.78 | 0.544 | -0.025 | 0 |
| fmt | T3m | up1 | 8 | 0.81 | 0.48 | 0.44 | 1.69 | 0.544 | -0.025 | 0 |
| flask | T0 | up1 | 9 | 0.72 | 0.40 | 0.39 | 1.81 | 0.524 | -0.092 | 22 |
| flask | T1 | up1 | 3 | 1.00 | 1.00 | 0.00 | 1.00 | 0.448 | 0.037 | 0 |
| flask | T1f | leaf | 22 | 0.78 | 0.27 | 0.64 | 2.90 | 0.472 | -0.113 | 0 |
| flask | T2 | up1 | 14 | 0.69 | 0.38 | 0.47 | 1.83 | 0.617 | -0.012 | 0 |
| flask | T3 | up1 | 10 | 0.74 | 0.39 | 0.44 | 1.90 | 0.704 | -0.058 | 0 |
| flask | T3m | up1 | 10 | 0.81 | 0.41 | 0.51 | 1.98 | 0.704 | -0.058 | 0 |

## C with `mistral-medium`

| repo | tree | view | modules | recall | share | excess recall | lift | B1 Q at that level | B2 Q at that level | empty nodes |
|---|---|---|---|---|---|---|---|---|---|---|
| ruby_llm | T0 | up1 | 17 | 0.65 | 0.15 | 0.48 | 4.24 | 0.670 | 0.047 | 8 |
| ruby_llm | T1 | up1 | 22 | 0.87 | 0.30 | 0.73 | 2.85 | 0.665 | 0.088 | 0 |
| ruby_llm | T1f | leaf | 108 | 0.66 | 0.04 | 0.64 | 16.41 | 0.638 | -0.024 | 0 |
| ruby_llm | T2 | up1 | 23 | 0.73 | 0.24 | 0.61 | 3.07 | 0.756 | 0.068 | 0 |
| ruby_llm | T3 | up1 | 12 | 0.87 | 0.27 | 0.62 | 3.17 | 0.824 | 0.131 | 0 |
| ruby_llm | T3m | up1 | 12 | 0.82 | 0.28 | 0.57 | 2.90 | 0.824 | 0.131 | 0 |
| gson | T0 | up1 | 8 | 0.64 | 0.46 | 0.25 | 1.38 | 0.313 | 0.039 | 16 |
| gson | T1 | up1 | 9 | 0.79 | 0.65 | 0.46 | 1.22 | 0.367 | 0.138 | 0 |
| gson | T1f | leaf | 83 | 0.52 | 0.11 | 0.48 | 4.67 | 0.498 | -0.040 | 0 |
| gson | T2 | top | 14 | 0.74 | 0.44 | 0.52 | 1.68 | 0.683 | 0.103 | 0 |
| gson | T3 | top | 7 | 0.86 | 0.65 | 0.44 | 1.33 | 0.660 | 0.080 | 0 |
| gson | T3m | top | 7 | 0.87 | 0.63 | 0.44 | 1.37 | 0.660 | 0.091 | 0 |
| tsdown | T0 | up1 | 9 | 0.74 | 0.47 | 0.40 | 1.57 | 0.282 | 0.007 | 0 |
| tsdown | T1 | up1 | 5 | 0.67 | 0.62 | 0.07 | 1.07 | 0.199 | 0.048 | 0 |
| tsdown | T1f | leaf | 38 | 0.63 | 0.12 | 0.54 | 5.31 | 0.272 | -0.050 | 0 |
| tsdown | T2 | up1 | 9 | 0.67 | 0.51 | 0.33 | 1.31 | 0.498 | -0.008 | 0 |
| tsdown | T3 | up1 | 7 | 0.70 | 0.47 | 0.27 | 1.47 | 0.481 | 0.045 | 0 |
| tsdown | T3m | up1 | 7 | 0.69 | 0.50 | 0.26 | 1.37 | 0.481 | 0.045 | 0 |
| fmt | T0 | up1 | 13 | 0.65 | 0.35 | 0.42 | 1.87 | 0.239 | 0.027 | 0 |
| fmt | T1 | up1 | 2 | 0.97 | 0.96 | -0.03 | 1.00 | -0.000 | -0.021 | 0 |
| fmt | T1f | leaf | 17 | 0.28 | 0.16 | 0.10 | 1.75 | 0.224 | -0.086 | 0 |
| fmt | T2 | up1 | 21 | 0.35 | 0.17 | 0.20 | 2.08 | 0.402 | -0.062 | 0 |
| fmt | T3 | up1 | 8 | 0.60 | 0.39 | 0.23 | 1.56 | 0.544 | -0.025 | 0 |
| fmt | T3m | up1 | 8 | 0.58 | 0.39 | 0.21 | 1.48 | 0.544 | -0.025 | 0 |
| flask | T0 | up1 | 9 | 0.81 | 0.39 | 0.48 | 2.08 | 0.524 | -0.092 | 22 |
| flask | T1 | up1 | 3 | 1.00 | 0.96 | 0.00 | 1.04 | 0.448 | 0.037 | 0 |
| flask | T1f | leaf | 22 | 0.69 | 0.22 | 0.55 | 3.16 | 0.472 | -0.113 | 0 |
| flask | T2 | up1 | 14 | 0.55 | 0.26 | 0.33 | 2.10 | 0.617 | -0.012 | 0 |
| flask | T3 | up1 | 10 | 0.72 | 0.37 | 0.42 | 1.92 | 0.704 | -0.058 | 0 |
| flask | T3m | up1 | 10 | 0.76 | 0.40 | 0.46 | 1.90 | 0.704 | -0.058 | 0 |

## Paired differences in excess recall (row tree minus column tree), 95% bootstrap interval over the 30 commits

A difference is called 'cannot tell' when the interval holds zero. Share of source lines differs between trees; read it with the table above.

Column 'modules' gives the module counts of the two views; when one is more than 1.5 times the other, the pair is flagged because excess recall at very different sizes is not a fair comparison.

| repo | model | comparison | modules | difference | 95% interval | verdict |
|---|---|---|---|---|---|---|
| ruby_llm | deepseek-flash | T3 - T0 | 12 / 17 | -0.00 | -0.09 to +0.10 | cannot tell |
| ruby_llm | deepseek-flash | T3 - T1 | 12 / 22 | -0.14 | -0.26 to -0.04 | first is worse (sizes too different) |
| ruby_llm | deepseek-flash | T2 - T0 | 23 / 17 | +0.07 | -0.09 to +0.24 | cannot tell |
| ruby_llm | deepseek-flash | T3 - T2 | 12 / 23 | -0.07 | -0.22 to +0.07 | cannot tell (sizes too different) |
| ruby_llm | deepseek-flash | T3m - T3 | 12 / 12 | +0.03 | +0.00 to +0.10 | cannot tell |
| ruby_llm | glm-flash | T3 - T0 | 12 / 17 | +0.01 | -0.08 to +0.12 | cannot tell |
| ruby_llm | glm-flash | T3 - T1 | 12 / 22 | -0.15 | -0.29 to -0.02 | first is worse (sizes too different) |
| ruby_llm | glm-flash | T2 - T0 | 23 / 17 | +0.07 | -0.09 to +0.24 | cannot tell |
| ruby_llm | glm-flash | T3 - T2 | 12 / 23 | -0.06 | -0.26 to +0.11 | cannot tell (sizes too different) |
| ruby_llm | glm-flash | T3m - T3 | 12 / 12 | +0.01 | +0.00 to +0.04 | cannot tell |
| ruby_llm | mistral-medium | T3 - T0 | 12 / 17 | +0.14 | +0.02 to +0.28 | first is better |
| ruby_llm | mistral-medium | T3 - T1 | 12 / 22 | -0.11 | -0.23 to +0.00 | cannot tell (sizes too different) |
| ruby_llm | mistral-medium | T2 - T0 | 23 / 17 | +0.13 | -0.07 to +0.33 | cannot tell |
| ruby_llm | mistral-medium | T3 - T2 | 12 / 23 | +0.01 | -0.14 to +0.17 | cannot tell (sizes too different) |
| ruby_llm | mistral-medium | T3m - T3 | 12 / 12 | -0.05 | -0.17 to +0.07 | cannot tell |
| gson | deepseek-flash | T3 - T0 | 7 / 8 | +0.23 | +0.08 to +0.39 | first is better |
| gson | deepseek-flash | T3 - T1 | 7 / 9 | -0.01 | -0.16 to +0.15 | cannot tell |
| gson | deepseek-flash | T2 - T0 | 14 / 8 | +0.26 | +0.07 to +0.46 | first is better (sizes too different) |
| gson | deepseek-flash | T3 - T2 | 7 / 14 | -0.03 | -0.16 to +0.09 | cannot tell (sizes too different) |
| gson | deepseek-flash | T3m - T3 | 7 / 7 | -0.06 | -0.15 to +0.00 | cannot tell |
| gson | glm-flash | T3 - T0 | 7 / 8 | +0.05 | -0.12 to +0.21 | cannot tell |
| gson | glm-flash | T3 - T1 | 7 / 9 | -0.08 | -0.19 to +0.05 | cannot tell |
| gson | glm-flash | T2 - T0 | 14 / 8 | +0.09 | -0.08 to +0.27 | cannot tell (sizes too different) |
| gson | glm-flash | T3 - T2 | 7 / 14 | -0.05 | -0.21 to +0.11 | cannot tell (sizes too different) |
| gson | glm-flash | T3m - T3 | 7 / 7 | -0.00 | -0.10 to +0.10 | cannot tell |
| gson | mistral-medium | T3 - T0 | 7 / 8 | +0.18 | +0.00 to +0.38 | first is better |
| gson | mistral-medium | T3 - T1 | 7 / 9 | -0.02 | -0.15 to +0.11 | cannot tell |
| gson | mistral-medium | T2 - T0 | 14 / 8 | +0.27 | +0.09 to +0.45 | first is better (sizes too different) |
| gson | mistral-medium | T3 - T2 | 7 / 14 | -0.08 | -0.24 to +0.09 | cannot tell (sizes too different) |
| gson | mistral-medium | T3m - T3 | 7 / 7 | +0.00 | -0.07 to +0.08 | cannot tell |
| tsdown | deepseek-flash | T3 - T0 | 7 / 9 | -0.07 | -0.20 to +0.07 | cannot tell |
| tsdown | deepseek-flash | T3 - T1 | 7 / 5 | +0.10 | -0.02 to +0.21 | cannot tell |
| tsdown | deepseek-flash | T2 - T0 | 9 / 9 | -0.11 | -0.24 to +0.04 | cannot tell |
| tsdown | deepseek-flash | T3 - T2 | 7 / 9 | +0.04 | -0.12 to +0.19 | cannot tell |
| tsdown | deepseek-flash | T3m - T3 | 7 / 7 | +0.03 | +0.00 to +0.10 | cannot tell |
| tsdown | glm-flash | T3 - T0 | 7 / 9 | -0.02 | -0.14 to +0.11 | cannot tell |
| tsdown | glm-flash | T3 - T1 | 7 / 5 | +0.17 | +0.04 to +0.31 | first is better |
| tsdown | glm-flash | T2 - T0 | 9 / 9 | -0.21 | -0.36 to -0.08 | first is worse |
| tsdown | glm-flash | T3 - T2 | 7 / 9 | +0.19 | +0.04 to +0.36 | first is better |
| tsdown | glm-flash | T3m - T3 | 7 / 7 | -0.05 | -0.17 to +0.05 | cannot tell |
| tsdown | mistral-medium | T3 - T0 | 7 / 9 | -0.14 | -0.33 to +0.06 | cannot tell |
| tsdown | mistral-medium | T3 - T1 | 7 / 5 | +0.20 | -0.01 to +0.41 | cannot tell |
| tsdown | mistral-medium | T2 - T0 | 9 / 9 | -0.07 | -0.26 to +0.12 | cannot tell |
| tsdown | mistral-medium | T3 - T2 | 7 / 9 | -0.07 | -0.26 to +0.13 | cannot tell |
| tsdown | mistral-medium | T3m - T3 | 7 / 7 | -0.01 | -0.14 to +0.12 | cannot tell |
| fmt | deepseek-flash | T3 - T0 | 8 / 13 | -0.20 | -0.39 to +0.00 | cannot tell (sizes too different) |
| fmt | deepseek-flash | T3 - T1 | 8 / 2 | +0.28 | +0.11 to +0.44 | first is better (sizes too different) |
| fmt | deepseek-flash | T2 - T0 | 21 / 13 | -0.03 | -0.15 to +0.08 | cannot tell (sizes too different) |
| fmt | deepseek-flash | T3 - T2 | 8 / 21 | -0.17 | -0.39 to +0.06 | cannot tell (sizes too different) |
| fmt | deepseek-flash | T3m - T3 | 8 / 8 | +0.07 | +0.00 to +0.17 | cannot tell |
| fmt | glm-flash | T3 - T0 | 8 / 13 | -0.09 | -0.24 to +0.07 | cannot tell (sizes too different) |
| fmt | glm-flash | T3 - T1 | 8 / 2 | +0.41 | +0.25 to +0.55 | first is better (sizes too different) |
| fmt | glm-flash | T2 - T0 | 21 / 13 | +0.08 | -0.09 to +0.24 | cannot tell (sizes too different) |
| fmt | glm-flash | T3 - T2 | 8 / 21 | -0.16 | -0.35 to +0.01 | cannot tell (sizes too different) |
| fmt | glm-flash | T3m - T3 | 8 / 8 | +0.03 | -0.07 to +0.13 | cannot tell |
| fmt | mistral-medium | T3 - T0 | 8 / 13 | -0.19 | -0.36 to -0.03 | first is worse (sizes too different) |
| fmt | mistral-medium | T3 - T1 | 8 / 2 | +0.26 | +0.07 to +0.46 | first is better (sizes too different) |
| fmt | mistral-medium | T2 - T0 | 21 / 13 | -0.22 | -0.40 to -0.07 | first is worse (sizes too different) |
| fmt | mistral-medium | T3 - T2 | 8 / 21 | +0.03 | -0.17 to +0.23 | cannot tell (sizes too different) |
| fmt | mistral-medium | T3m - T3 | 8 / 8 | -0.02 | -0.13 to +0.10 | cannot tell |
| flask | deepseek-flash | T3 - T0 | 10 / 9 | +0.04 | -0.11 to +0.19 | cannot tell |
| flask | deepseek-flash | T3 - T1 | 10 / 3 | +0.48 | +0.34 to +0.60 | first is better (sizes too different) |
| flask | deepseek-flash | T2 - T0 | 14 / 9 | +0.09 | -0.08 to +0.25 | cannot tell (sizes too different) |
| flask | deepseek-flash | T3 - T2 | 10 / 14 | -0.05 | -0.17 to +0.06 | cannot tell |
| flask | deepseek-flash | T3m - T3 | 10 / 10 | +0.01 | -0.04 to +0.05 | cannot tell |
| flask | glm-flash | T3 - T0 | 10 / 9 | +0.05 | -0.12 to +0.21 | cannot tell |
| flask | glm-flash | T3 - T1 | 10 / 3 | +0.44 | +0.29 to +0.58 | first is better (sizes too different) |
| flask | glm-flash | T2 - T0 | 14 / 9 | +0.07 | -0.03 to +0.18 | cannot tell (sizes too different) |
| flask | glm-flash | T3 - T2 | 10 / 14 | -0.02 | -0.19 to +0.13 | cannot tell |
| flask | glm-flash | T3m - T3 | 10 / 10 | +0.07 | -0.04 to +0.19 | cannot tell |
| flask | mistral-medium | T3 - T0 | 10 / 9 | -0.06 | -0.24 to +0.11 | cannot tell |
| flask | mistral-medium | T3 - T1 | 10 / 3 | +0.42 | +0.27 to +0.56 | first is better (sizes too different) |
| flask | mistral-medium | T2 - T0 | 14 / 9 | -0.15 | -0.32 to +0.02 | cannot tell (sizes too different) |
| flask | mistral-medium | T3 - T2 | 10 / 14 | +0.09 | -0.08 to +0.24 | cannot tell |
| flask | mistral-medium | T3m - T3 | 10 / 10 | +0.04 | -0.01 to +0.11 | cannot tell |
