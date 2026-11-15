# Offline model experiments (Nov 14, current board positions)

Data: 3 training rounds + 1 separate test round of the 4-class routine, labelled by the guided prompt (first 2 s of each step skipped). Balanced training (no class above 2x the smallest).

- **LORO**: balanced accuracy, train on 2 training rounds, score the 3rd (3 folds).
- **TEST**: balanced accuracy, train on all 3, score the separate test round.
- **false alerts / missed alerts**: per step, using the live rule (3 s smoothing, alert after 3 s lying), over LORO folds + test.

Current live setup (2 s, Haven features, kNN7, all paths): LORO 0.74, TEST 0.87, false alerts 4/16, missed alerts 1/12.

| rank | window | features | paths | model | LORO | TEST | lying recall (test) | false alerts | missed alerts |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 s | haven | 1>2+1>3+2>3 | SVM-RBF | 0.86 | 0.93 | 1.00 | 3/16 | 0/12 |
| 2 | 3 s | haven+summary | 1>2+1>3+2>3 | SVM-RBF | 0.86 | 0.93 | 1.00 | 3/16 | 0/12 |
| 3 | 2 s | haven | 1>2+1>3+2>3 | SVM-RBF | 0.85 | 0.91 | 1.00 | 3/16 | 0/12 |
| 4 | 2 s | haven+summary | 1>2+1>3+2>3 | SVM-RBF | 0.85 | 0.91 | 1.00 | 3/16 | 0/12 |
| 5 | 3 s | shape-smooth | 1>2+1>3+2>3 | SVM-RBF | 0.83 | 0.93 | 1.00 | 3/16 | 0/12 |
| 6 | 2 s | shape-smooth | 1>2+1>3+2>3 | SVM-RBF | 0.84 | 0.91 | 1.00 | 3/16 | 0/12 |
| 7 | 1 s | haven | 1>2+1>3+2>3 | SVM-RBF | 0.85 | 0.89 | 1.00 | 3/16 | 0/12 |
| 8 | 1 s | haven+summary | 1>2+1>3+2>3 | SVM-RBF | 0.84 | 0.89 | 1.00 | 3/16 | 0/12 |
| 9 | 1 s | shape-smooth | 1>2+1>3+2>3 | SVM-RBF | 0.84 | 0.88 | 1.00 | 3/16 | 0/12 |
| 10 | 2 s | haven | 1>3+2>3 | kNN7 (live) | 0.71 | 0.78 | 1.00 | 3/16 | 1/12 |
| 11 | 3 s | haven | 1>2+1>3+2>3 | kNN7 (live) | 0.76 | 0.87 | 1.00 | 4/16 | 0/12 |
| 12 | 3 s | haven+summary | 1>2+1>3+2>3 | MLP (neural net) | 0.72 | 0.90 | 1.00 | 4/16 | 0/12 |
| 13 | 3 s | shape-smooth | 1>2+1>3+2>3 | MLP (neural net) | 0.67 | 0.93 | 1.00 | 4/16 | 0/12 |
| 14 | 1 s | shape-smooth | 1>2+1>3+2>3 | MLP (neural net) | 0.71 | 0.86 | 0.97 | 4/16 | 0/12 |
| 15 | 1 s | haven | 1>2+1>3+2>3 | kNN7 (live) | 0.75 | 0.79 | 1.00 | 4/16 | 0/12 |
| 16 | 1 s | haven+summary | 1>2+1>3+2>3 | kNN7 (live) | 0.75 | 0.78 | 1.00 | 4/16 | 0/12 |
| 17 | 2 s | haven+summary | 1>2+1>3+2>3 | kNN7 (live) | 0.74 | 0.87 | 1.00 | 4/16 | 1/12 |
| 18 | 2 s | haven | 1>2+1>3+2>3 | kNN7 (live) | 0.74 | 0.87 | 1.00 | 4/16 | 1/12 |
| 19 | 3 s | haven | 1>2+1>3+2>3 | ExtraTrees | 0.79 | 0.93 | 1.00 | 5/16 | 0/12 |
| 20 | 3 s | shape-smooth | 1>2+1>3+2>3 | ExtraTrees | 0.79 | 0.93 | 1.00 | 5/16 | 0/12 |
| 21 | 3 s | haven+summary | 1>2+1>3+2>3 | ExtraTrees | 0.79 | 0.93 | 1.00 | 5/16 | 0/12 |
| 22 | 2 s | shape-smooth | 1>2+1>3+2>3 | ExtraTrees | 0.78 | 0.92 | 1.00 | 5/16 | 0/12 |
| 23 | 1 s | shape-smooth | 1>2+1>3+2>3 | ExtraTrees | 0.78 | 0.91 | 1.00 | 5/16 | 0/12 |
| 24 | 1 s | haven+summary | 1>2+1>3+2>3 | ExtraTrees | 0.79 | 0.91 | 1.00 | 5/16 | 0/12 |
| 25 | 2 s | haven+summary | 1>2+1>3+2>3 | ExtraTrees | 0.78 | 0.90 | 1.00 | 5/16 | 0/12 |
| 26 | 1 s | haven | 1>2+1>3+2>3 | ExtraTrees | 0.77 | 0.91 | 1.00 | 5/16 | 0/12 |
| 27 | 2 s | haven | 1>2+1>3+2>3 | ExtraTrees | 0.78 | 0.89 | 1.00 | 5/16 | 0/12 |
| 28 | 2 s | shape-smooth | 1>2+1>3+2>3 | MLP (neural net) | 0.69 | 0.90 | 0.99 | 5/16 | 0/12 |
| 29 | 3 s | shape-smooth | 1>2+1>3+2>3 | kNN7 (live) | 0.73 | 0.81 | 1.00 | 5/16 | 0/12 |
| 30 | 1 s | haven+summary | 1>2+1>3+2>3 | MLP (neural net) | 0.72 | 0.80 | 1.00 | 5/16 | 0/12 |
| 31 | 2 s | haven+summary | 1>2+1>3+2>3 | MLP (neural net) | 0.76 | 0.73 | 1.00 | 5/16 | 0/12 |
| 32 | 2 s | haven | 1>2+2>3 | kNN7 (live) | 0.74 | 0.75 | 1.00 | 5/16 | 0/12 |
| 33 | 3 s | haven+summary | 1>2+1>3+2>3 | LogReg | 0.77 | 0.71 | 1.00 | 5/16 | 0/12 |
| 34 | 1 s | motion | 1>2+1>3+2>3 | SVM-RBF | 0.51 | 0.75 | 0.69 | 5/16 | 0/12 |
| 35 | 3 s | haven+summary | 1>2+1>3+2>3 | kNN7 (live) | 0.76 | 0.87 | 1.00 | 5/16 | 1/12 |
| 36 | 3 s | haven | 1>2+1>3+2>3 | MLP (neural net) | 0.65 | 0.89 | 1.00 | 5/16 | 1/12 |
| 37 | 3 s | motion | 1>2+1>3+2>3 | SVM-RBF | 0.57 | 0.82 | 0.84 | 5/16 | 1/12 |
| 38 | 3 s | shape-smooth | 1>2+1>3+2>3 | LogReg | 0.73 | 0.86 | 1.00 | 6/16 | 0/12 |
| 39 | 2 s | shape-smooth | 1>2+1>3+2>3 | LogReg | 0.74 | 0.82 | 1.00 | 6/16 | 0/12 |
| 40 | 2 s | shape-smooth | 1>2+1>3+2>3 | kNN7 (live) | 0.73 | 0.82 | 1.00 | 6/16 | 0/12 |
| 41 | 1 s | haven | 1>2+1>3+2>3 | MLP (neural net) | 0.70 | 0.83 | 1.00 | 6/16 | 0/12 |
| 42 | 1 s | shape-smooth | 1>2+1>3+2>3 | kNN7 (live) | 0.73 | 0.80 | 1.00 | 6/16 | 0/12 |
| 43 | 1 s | shape-smooth | 1>2+1>3+2>3 | LogReg | 0.71 | 0.79 | 1.00 | 6/16 | 0/12 |
| 44 | 2 s | haven | 1>2+1>3+2>3 | LogReg | 0.76 | 0.72 | 1.00 | 6/16 | 0/12 |
| 45 | 2 s | haven+summary | 1>2+1>3+2>3 | LogReg | 0.76 | 0.72 | 1.00 | 6/16 | 0/12 |
| 46 | 3 s | haven | 1>2+1>3+2>3 | LogReg | 0.76 | 0.71 | 1.00 | 6/16 | 0/12 |
| 47 | 1 s | haven+summary | 1>2+1>3+2>3 | LogReg | 0.74 | 0.69 | 1.00 | 6/16 | 0/12 |
| 48 | 1 s | haven | 1>2+1>3+2>3 | LogReg | 0.74 | 0.69 | 1.00 | 6/16 | 0/12 |
| 49 | 3 s | motion | 1>2+1>3+2>3 | LogReg | 0.60 | 0.83 | 0.97 | 6/16 | 0/12 |
| 50 | 2 s | motion | 1>2+1>3+2>3 | LogReg | 0.57 | 0.79 | 0.93 | 6/16 | 0/12 |
| 51 | 2 s | haven | 1>2+1>3+2>3 | MLP (neural net) | 0.72 | 0.76 | 1.00 | 6/16 | 1/12 |
| 52 | 2 s | motion | 1>2+1>3+2>3 | MLP (neural net) | 0.53 | 0.80 | 0.85 | 6/16 | 3/12 |
| 53 | 1 s | motion | 1>2+1>3+2>3 | MLP (neural net) | 0.50 | 0.75 | 0.89 | 7/16 | 0/12 |
| 54 | 2 s | motion | 1>2+1>3+2>3 | SVM-RBF | 0.56 | 0.80 | 0.75 | 7/16 | 1/12 |
| 55 | 2 s | motion | 1>2+1>3+2>3 | kNN7 (live) | 0.53 | 0.74 | 0.63 | 7/16 | 1/12 |
| 56 | 2 s | haven | 1>2+1>3 | kNN7 (live) | 0.68 | 0.71 | 0.51 | 7/16 | 2/12 |
| 57 | 3 s | motion | 1>2+1>3+2>3 | MLP (neural net) | 0.53 | 0.86 | 0.95 | 8/16 | 1/12 |
| 58 | 3 s | motion | 1>2+1>3+2>3 | kNN7 (live) | 0.55 | 0.68 | 0.50 | 8/16 | 3/12 |
| 59 | 1 s | motion | 1>2+1>3+2>3 | LogReg | 0.52 | 0.75 | 0.86 | 9/16 | 0/12 |
| 60 | 3 s | motion | 1>2+1>3+2>3 | ExtraTrees | 0.56 | 0.71 | 0.98 | 9/16 | 1/12 |
| 61 | 1 s | motion | 1>2+1>3+2>3 | kNN7 (live) | 0.50 | 0.58 | 0.43 | 9/16 | 3/12 |
| 62 | 2 s | motion | 1>2+1>3+2>3 | ExtraTrees | 0.54 | 0.70 | 1.00 | 10/16 | 1/12 |
| 63 | 1 s | motion | 1>2+1>3+2>3 | ExtraTrees | 0.51 | 0.63 | 0.93 | 10/16 | 1/12 |
