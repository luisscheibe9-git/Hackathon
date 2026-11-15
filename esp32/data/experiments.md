# Offline model experiments (Nov 14, current board positions)

Data: 3 training rounds + 1 separate test round of the 4-class routine, labelled by the guided prompt (first 2 s of each step skipped). Balanced training (no class above 2x the smallest).

- **LORO**: balanced accuracy, train on 2 training rounds, score the 3rd (3 folds).
- **TEST**: balanced accuracy, train on all 3, score the separate test round.
- **false alerts / missed alerts**: per step, using the live rule (3 s smoothing, alert after 3 s lying), over LORO folds + test.

Current live setup (2 s, Haven features, kNN7, all paths): LORO 0.86, TEST 0.95, false alerts 0/12, missed alerts 2/20.

| rank | window | features | paths | model | LORO | TEST | lying recall (test) | false alerts | missed alerts |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 s | haven | 1>2+1>3+2>3 | kNN7 (live) | 0.85 | 1.00 | 0.99 | 0/12 | 1/20 |
| 2 | 3 s | haven+summary | 1>2+1>3+2>3 | kNN7 (live) | 0.85 | 1.00 | 0.99 | 0/12 | 1/20 |
| 3 | 3 s | shape-smooth | 1>2+1>3+2>3 | kNN7 (live) | 0.82 | 0.97 | 0.95 | 0/12 | 1/20 |
| 4 | 2 s | haven+summary | 1>2+1>3+2>3 | kNN7 (live) | 0.86 | 0.93 | 0.84 | 0/12 | 1/20 |
| 5 | 1 s | haven | 1>2+1>3+2>3 | kNN7 (live) | 0.83 | 0.89 | 0.76 | 0/12 | 1/20 |
| 6 | 1 s | haven+summary | 1>2+1>3+2>3 | kNN7 (live) | 0.82 | 0.89 | 0.75 | 0/12 | 1/20 |
| 7 | 1 s | shape-smooth | 1>2+1>3+2>3 | kNN7 (live) | 0.78 | 0.85 | 0.55 | 0/12 | 1/20 |
| 8 | 2 s | haven | 1>2+1>3+2>3 | kNN7 (live) | 0.86 | 0.95 | 0.84 | 0/12 | 2/20 |
| 9 | 2 s | shape-smooth | 1>2+1>3+2>3 | kNN7 (live) | 0.81 | 0.92 | 0.79 | 0/12 | 2/20 |
| 10 | 3 s | haven+summary | 1>2+1>3+2>3 | MLP (neural net) | 0.80 | 0.90 | 0.80 | 0/12 | 3/20 |
| 11 | 3 s | haven+summary | 1>2+1>3+2>3 | ExtraTrees | 0.81 | 0.98 | 0.91 | 1/12 | 0/20 |
| 12 | 2 s | haven | 1>3+2>3 | kNN7 (live) | 0.77 | 0.95 | 0.80 | 1/12 | 0/20 |
| 13 | 1 s | shape-smooth | 1>2+1>3+2>3 | ExtraTrees | 0.76 | 0.91 | 0.89 | 1/12 | 0/20 |
| 14 | 3 s | haven | 1>2+1>3+2>3 | LogReg | 0.80 | 0.86 | 0.89 | 1/12 | 0/20 |
| 15 | 3 s | haven+summary | 1>2+1>3+2>3 | LogReg | 0.80 | 0.86 | 0.89 | 1/12 | 0/20 |
| 16 | 2 s | haven | 1>2+1>3+2>3 | MLP (neural net) | 0.69 | 0.76 | 0.80 | 1/12 | 0/20 |
| 17 | 3 s | haven | 1>2+1>3+2>3 | ExtraTrees | 0.84 | 0.99 | 0.94 | 1/12 | 1/20 |
| 18 | 3 s | shape-smooth | 1>2+1>3+2>3 | LogReg | 0.80 | 0.96 | 0.85 | 1/12 | 1/20 |
| 19 | 2 s | shape-smooth | 1>2+1>3+2>3 | LogReg | 0.79 | 0.89 | 0.77 | 1/12 | 1/20 |
| 20 | 3 s | motion | 1>2+1>3+2>3 | kNN7 (live) | 0.74 | 0.72 | 0.86 | 1/12 | 1/20 |
| 21 | 2 s | haven | 1>2+1>3+2>3 | ExtraTrees | 0.81 | 0.93 | 0.88 | 1/12 | 2/20 |
| 22 | 2 s | haven+summary | 1>2+1>3+2>3 | ExtraTrees | 0.79 | 0.91 | 0.88 | 1/12 | 2/20 |
| 23 | 1 s | haven | 1>2+1>3+2>3 | SVM-RBF | 0.76 | 0.93 | 0.90 | 1/12 | 2/20 |
| 24 | 1 s | shape-smooth | 1>2+1>3+2>3 | SVM-RBF | 0.75 | 0.93 | 0.86 | 1/12 | 2/20 |
| 25 | 1 s | haven+summary | 1>2+1>3+2>3 | SVM-RBF | 0.75 | 0.93 | 0.91 | 1/12 | 2/20 |
| 26 | 2 s | haven | 1>2+1>3+2>3 | LogReg | 0.77 | 0.87 | 0.77 | 1/12 | 2/20 |
| 27 | 2 s | haven+summary | 1>2+1>3+2>3 | LogReg | 0.77 | 0.87 | 0.77 | 1/12 | 2/20 |
| 28 | 1 s | haven | 1>2+1>3+2>3 | MLP (neural net) | 0.67 | 0.88 | 0.78 | 1/12 | 2/20 |
| 29 | 1 s | haven+summary | 1>2+1>3+2>3 | ExtraTrees | 0.80 | 0.95 | 0.86 | 1/12 | 3/20 |
| 30 | 1 s | haven | 1>2+1>3+2>3 | ExtraTrees | 0.80 | 0.95 | 0.86 | 1/12 | 3/20 |
| 31 | 1 s | shape-smooth | 1>2+1>3+2>3 | LogReg | 0.75 | 0.88 | 0.76 | 1/12 | 3/20 |
| 32 | 1 s | haven+summary | 1>2+1>3+2>3 | LogReg | 0.76 | 0.89 | 0.76 | 1/12 | 4/20 |
| 33 | 1 s | haven | 1>2+1>3+2>3 | LogReg | 0.76 | 0.89 | 0.74 | 1/12 | 4/20 |
| 34 | 3 s | shape-smooth | 1>2+1>3+2>3 | ExtraTrees | 0.78 | 0.97 | 1.00 | 2/12 | 0/20 |
| 35 | 2 s | shape-smooth | 1>2+1>3+2>3 | SVM-RBF | 0.74 | 0.97 | 0.96 | 2/12 | 0/20 |
| 36 | 2 s | shape-smooth | 1>2+1>3+2>3 | ExtraTrees | 0.76 | 0.94 | 0.90 | 2/12 | 0/20 |
| 37 | 2 s | haven+summary | 1>2+1>3+2>3 | SVM-RBF | 0.73 | 0.94 | 0.97 | 2/12 | 0/20 |
| 38 | 2 s | haven | 1>2+1>3+2>3 | SVM-RBF | 0.72 | 0.93 | 0.97 | 2/12 | 0/20 |
| 39 | 2 s | haven | 1>2+1>3 | kNN7 (live) | 0.58 | 0.93 | 0.89 | 2/12 | 0/20 |
| 40 | 1 s | motion | 1>2+1>3+2>3 | SVM-RBF | 0.67 | 0.57 | 0.78 | 2/12 | 1/20 |
| 41 | 1 s | motion | 1>2+1>3+2>3 | kNN7 (live) | 0.66 | 0.57 | 0.57 | 2/12 | 1/20 |
| 42 | 1 s | haven+summary | 1>2+1>3+2>3 | MLP (neural net) | 0.78 | 0.90 | 0.71 | 2/12 | 2/20 |
| 43 | 2 s | haven+summary | 1>2+1>3+2>3 | MLP (neural net) | 0.80 | 0.77 | 0.77 | 2/12 | 2/20 |
| 44 | 2 s | haven | 1>2+2>3 | kNN7 (live) | 0.76 | 0.72 | 0.57 | 2/12 | 4/20 |
| 45 | 3 s | haven+summary | 1>2+1>3+2>3 | SVM-RBF | 0.70 | 1.00 | 1.00 | 3/12 | 0/20 |
| 46 | 3 s | haven | 1>2+1>3+2>3 | SVM-RBF | 0.69 | 1.00 | 1.00 | 3/12 | 0/20 |
| 47 | 3 s | shape-smooth | 1>2+1>3+2>3 | SVM-RBF | 0.67 | 1.00 | 1.00 | 3/12 | 0/20 |
| 48 | 1 s | motion | 1>2+1>3+2>3 | LogReg | 0.71 | 0.62 | 0.77 | 3/12 | 1/20 |
| 49 | 2 s | motion | 1>2+1>3+2>3 | MLP (neural net) | 0.62 | 0.62 | 0.69 | 3/12 | 2/20 |
| 50 | 3 s | motion | 1>2+1>3+2>3 | MLP (neural net) | 0.56 | 0.54 | 0.72 | 3/12 | 2/20 |
| 51 | 1 s | motion | 1>2+1>3+2>3 | MLP (neural net) | 0.59 | 0.60 | 0.50 | 3/12 | 3/20 |
| 52 | 3 s | haven | 1>2+1>3+2>3 | MLP (neural net) | 0.66 | 0.59 | 0.86 | 4/12 | 0/20 |
| 53 | 2 s | shape-smooth | 1>2+1>3+2>3 | MLP (neural net) | 0.71 | 0.86 | 0.85 | 4/12 | 1/20 |
| 54 | 1 s | shape-smooth | 1>2+1>3+2>3 | MLP (neural net) | 0.68 | 0.75 | 0.86 | 4/12 | 1/20 |
| 55 | 3 s | motion | 1>2+1>3+2>3 | LogReg | 0.74 | 0.54 | 0.95 | 4/12 | 1/20 |
| 56 | 2 s | motion | 1>2+1>3+2>3 | kNN7 (live) | 0.61 | 0.64 | 0.69 | 4/12 | 1/20 |
| 57 | 2 s | motion | 1>2+1>3+2>3 | LogReg | 0.70 | 0.52 | 0.83 | 4/12 | 1/20 |
| 58 | 3 s | shape-smooth | 1>2+1>3+2>3 | MLP (neural net) | 0.66 | 0.96 | 0.85 | 4/12 | 2/20 |
| 59 | 3 s | motion | 1>2+1>3+2>3 | ExtraTrees | 0.58 | 0.59 | 0.98 | 7/12 | 0/20 |
| 60 | 1 s | motion | 1>2+1>3+2>3 | ExtraTrees | 0.66 | 0.64 | 0.86 | 7/12 | 1/20 |
| 61 | 2 s | motion | 1>2+1>3+2>3 | SVM-RBF | 0.63 | 0.53 | 0.94 | 7/12 | 1/20 |
| 62 | 3 s | motion | 1>2+1>3+2>3 | SVM-RBF | 0.56 | 0.58 | 1.00 | 7/12 | 1/20 |
| 63 | 2 s | motion | 1>2+1>3+2>3 | ExtraTrees | 0.61 | 0.59 | 0.90 | 8/12 | 0/20 |
