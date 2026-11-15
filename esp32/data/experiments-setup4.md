# Offline model experiments (Nov 14, current board positions)

Data: 3 training rounds + 1 separate test round of the 4-class routine, labelled by the guided prompt (first 2 s of each step skipped). Balanced training (no class above 2x the smallest).

- **LORO**: balanced accuracy, train on 2 training rounds, score the 3rd (3 folds).
- **TEST**: balanced accuracy, train on all 3, score the separate test round.
- **false alerts / missed alerts**: per step, using the live rule (3 s smoothing, alert after 3 s lying), over LORO folds + test.

Current live setup (2 s, Haven features, kNN7, all paths): LORO 0.73, TEST 0.77, false alerts 1/12, missed alerts 6/20.

| rank | window | features | paths | model | LORO | TEST | lying recall (test) | false alerts | missed alerts |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 s | motion | 1>2+1>3+2>3 | kNN7 (live) | 0.62 | 0.58 | 0.49 | 0/12 | 7/20 |
| 2 | 2 s | motion | 1>2+1>3+2>3 | kNN7 (live) | 0.61 | 0.47 | 0.35 | 0/12 | 7/20 |
| 3 | 1 s | motion | 1>2+1>3+2>3 | kNN7 (live) | 0.57 | 0.50 | 0.22 | 0/12 | 8/20 |
| 4 | 1 s | haven+summary | 1>2+1>3+2>3 | MLP (neural net) | 0.68 | 0.69 | 0.74 | 1/12 | 3/20 |
| 5 | 2 s | haven+summary | 1>2+1>3+2>3 | MLP (neural net) | 0.65 | 0.69 | 0.77 | 1/12 | 3/20 |
| 6 | 3 s | motion | 1>2+1>3+2>3 | LogReg | 0.62 | 0.60 | 0.42 | 1/12 | 4/20 |
| 7 | 1 s | haven | 1>2+1>3+2>3 | kNN7 (live) | 0.72 | 0.77 | 0.68 | 1/12 | 5/20 |
| 8 | 1 s | haven+summary | 1>2+1>3+2>3 | kNN7 (live) | 0.71 | 0.78 | 0.69 | 1/12 | 5/20 |
| 9 | 2 s | motion | 1>2+1>3+2>3 | LogReg | 0.58 | 0.62 | 0.33 | 1/12 | 5/20 |
| 10 | 3 s | motion | 1>2+1>3+2>3 | MLP (neural net) | 0.58 | 0.57 | 0.72 | 1/12 | 5/20 |
| 11 | 2 s | haven | 1>2+1>3+2>3 | kNN7 (live) | 0.73 | 0.77 | 0.71 | 1/12 | 6/20 |
| 12 | 3 s | haven | 1>2+1>3+2>3 | kNN7 (live) | 0.71 | 0.79 | 0.64 | 1/12 | 6/20 |
| 13 | 2 s | haven+summary | 1>2+1>3+2>3 | kNN7 (live) | 0.72 | 0.76 | 0.70 | 1/12 | 6/20 |
| 14 | 3 s | haven | 1>2+1>3+2>3 | LogReg | 0.67 | 0.64 | 0.57 | 1/12 | 6/20 |
| 15 | 1 s | shape-smooth | 1>2+1>3+2>3 | LogReg | 0.67 | 0.63 | 0.46 | 1/12 | 6/20 |
| 16 | 3 s | shape-smooth | 1>2+1>3+2>3 | LogReg | 0.68 | 0.62 | 0.47 | 1/12 | 6/20 |
| 17 | 1 s | haven | 1>2+1>3+2>3 | LogReg | 0.65 | 0.65 | 0.52 | 1/12 | 6/20 |
| 18 | 1 s | haven+summary | 1>2+1>3+2>3 | LogReg | 0.65 | 0.64 | 0.51 | 1/12 | 6/20 |
| 19 | 2 s | haven | 1>2+1>3+2>3 | LogReg | 0.65 | 0.63 | 0.54 | 1/12 | 6/20 |
| 20 | 2 s | shape-smooth | 1>2+1>3+2>3 | LogReg | 0.65 | 0.63 | 0.54 | 1/12 | 6/20 |
| 21 | 2 s | haven+summary | 1>2+1>3+2>3 | LogReg | 0.64 | 0.63 | 0.54 | 1/12 | 6/20 |
| 22 | 3 s | haven+summary | 1>2+1>3+2>3 | LogReg | 0.64 | 0.63 | 0.52 | 1/12 | 6/20 |
| 23 | 2 s | motion | 1>2+1>3+2>3 | MLP (neural net) | 0.56 | 0.61 | 0.61 | 1/12 | 6/20 |
| 24 | 3 s | haven+summary | 1>2+1>3+2>3 | kNN7 (live) | 0.71 | 0.73 | 0.60 | 1/12 | 7/20 |
| 25 | 3 s | haven+summary | 1>2+1>3+2>3 | MLP (neural net) | 0.71 | 0.60 | 0.41 | 1/12 | 7/20 |
| 26 | 1 s | motion | 1>2+1>3+2>3 | ExtraTrees | 0.54 | 0.72 | 0.56 | 2/12 | 1/20 |
| 27 | 2 s | shape-smooth | 1>2+1>3+2>3 | ExtraTrees | 0.55 | 0.69 | 0.75 | 2/12 | 1/20 |
| 28 | 3 s | shape-smooth | 1>2+1>3+2>3 | ExtraTrees | 0.57 | 0.69 | 0.75 | 2/12 | 2/20 |
| 29 | 2 s | haven | 1>2+1>3+2>3 | ExtraTrees | 0.55 | 0.70 | 0.79 | 2/12 | 2/20 |
| 30 | 1 s | shape-smooth | 1>2+1>3+2>3 | kNN7 (live) | 0.73 | 0.70 | 0.74 | 2/12 | 4/20 |
| 31 | 1 s | motion | 1>2+1>3+2>3 | LogReg | 0.53 | 0.61 | 0.28 | 2/12 | 5/20 |
| 32 | 2 s | shape-smooth | 1>2+1>3+2>3 | kNN7 (live) | 0.72 | 0.72 | 0.74 | 2/12 | 6/20 |
| 33 | 3 s | shape-smooth | 1>2+1>3+2>3 | kNN7 (live) | 0.73 | 0.67 | 0.68 | 2/12 | 6/20 |
| 34 | 3 s | haven | 1>2+1>3+2>3 | ExtraTrees | 0.57 | 0.74 | 0.95 | 3/12 | 1/20 |
| 35 | 3 s | haven+summary | 1>2+1>3+2>3 | ExtraTrees | 0.53 | 0.74 | 0.97 | 3/12 | 1/20 |
| 36 | 1 s | haven+summary | 1>2+1>3+2>3 | ExtraTrees | 0.52 | 0.73 | 0.78 | 3/12 | 1/20 |
| 37 | 2 s | motion | 1>2+1>3+2>3 | SVM-RBF | 0.63 | 0.45 | 0.91 | 3/12 | 1/20 |
| 38 | 2 s | haven+summary | 1>2+1>3+2>3 | ExtraTrees | 0.56 | 0.72 | 0.87 | 3/12 | 2/20 |
| 39 | 1 s | motion | 1>2+1>3+2>3 | MLP (neural net) | 0.61 | 0.58 | 0.69 | 3/12 | 2/20 |
| 40 | 1 s | motion | 1>2+1>3+2>3 | SVM-RBF | 0.59 | 0.59 | 0.86 | 3/12 | 2/20 |
| 41 | 1 s | shape-smooth | 1>2+1>3+2>3 | ExtraTrees | 0.58 | 0.66 | 0.49 | 3/12 | 4/20 |
| 42 | 2 s | haven | 1>2+1>3 | kNN7 (live) | 0.56 | 0.40 | 0.68 | 3/12 | 9/20 |
| 43 | 3 s | motion | 1>2+1>3+2>3 | ExtraTrees | 0.52 | 0.74 | 0.88 | 4/12 | 1/20 |
| 44 | 2 s | motion | 1>2+1>3+2>3 | ExtraTrees | 0.51 | 0.74 | 0.63 | 4/12 | 1/20 |
| 45 | 1 s | haven | 1>2+1>3+2>3 | ExtraTrees | 0.54 | 0.71 | 0.78 | 4/12 | 2/20 |
| 46 | 2 s | haven | 1>2+1>3+2>3 | MLP (neural net) | 0.67 | 0.52 | 0.90 | 4/12 | 3/20 |
| 47 | 1 s | shape-smooth | 1>2+1>3+2>3 | MLP (neural net) | 0.55 | 0.62 | 0.47 | 4/12 | 4/20 |
| 48 | 1 s | haven | 1>2+1>3+2>3 | MLP (neural net) | 0.63 | 0.48 | 0.87 | 4/12 | 4/20 |
| 49 | 2 s | shape-smooth | 1>2+1>3+2>3 | MLP (neural net) | 0.55 | 0.67 | 0.69 | 4/12 | 5/20 |
| 50 | 2 s | haven | 1>3+2>3 | kNN7 (live) | 0.50 | 0.56 | 0.06 | 4/12 | 12/20 |
| 51 | 3 s | haven+summary | 1>2+1>3+2>3 | SVM-RBF | 0.61 | 0.40 | 1.00 | 5/12 | 2/20 |
| 52 | 3 s | shape-smooth | 1>2+1>3+2>3 | SVM-RBF | 0.61 | 0.37 | 1.00 | 5/12 | 2/20 |
| 53 | 3 s | haven | 1>2+1>3+2>3 | SVM-RBF | 0.61 | 0.37 | 1.00 | 5/12 | 2/20 |
| 54 | 1 s | haven+summary | 1>2+1>3+2>3 | SVM-RBF | 0.63 | 0.53 | 0.92 | 5/12 | 3/20 |
| 55 | 1 s | haven | 1>2+1>3+2>3 | SVM-RBF | 0.64 | 0.52 | 0.92 | 5/12 | 3/20 |
| 56 | 1 s | shape-smooth | 1>2+1>3+2>3 | SVM-RBF | 0.66 | 0.52 | 0.92 | 5/12 | 4/20 |
| 57 | 2 s | haven | 1>2+2>3 | kNN7 (live) | 0.61 | 0.50 | 0.88 | 5/12 | 6/20 |
| 58 | 3 s | shape-smooth | 1>2+1>3+2>3 | MLP (neural net) | 0.38 | 0.70 | 0.80 | 5/12 | 6/20 |
| 59 | 3 s | motion | 1>2+1>3+2>3 | SVM-RBF | 0.63 | 0.40 | 1.00 | 6/12 | 1/20 |
| 60 | 2 s | haven+summary | 1>2+1>3+2>3 | SVM-RBF | 0.58 | 0.47 | 0.98 | 6/12 | 3/20 |
| 61 | 2 s | shape-smooth | 1>2+1>3+2>3 | SVM-RBF | 0.58 | 0.45 | 0.98 | 6/12 | 3/20 |
| 62 | 2 s | haven | 1>2+1>3+2>3 | SVM-RBF | 0.58 | 0.45 | 0.98 | 6/12 | 3/20 |
| 63 | 3 s | haven | 1>2+1>3+2>3 | MLP (neural net) | 0.56 | 0.49 | 0.83 | 6/12 | 4/20 |
