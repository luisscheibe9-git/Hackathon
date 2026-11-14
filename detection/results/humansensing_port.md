# ESP32-WiFi-CSI-Human-Sensing port: leave-one-trial-out

Port of github.com/everythingfreee/ESP32-WiFi-CSI-Human-Sensing (MIT, (c) 2026 Sanaullah Shaheer): EMA preprocessing, Hampel filter, their 180-dim features, KNN(k=7) and RF(200 trees) candidates, and their movement heuristic (threshold = 1.5 x mean empty-room move_rel_activity, taken from the training trials). Folds = held-out trial.

## Window 1 s (12 samples, stride 2)

Windows per class: empty 310, standing 320, walking 327

| method | task | LOTO acc | per held-out trial | confusion (rows=true) |
|---|---|---|---|---|
| movement heuristic | moving vs still | 0.672 | {1: 0.684, 2: 0.652, 3: 0.681} | [[569, 61], [253, 74]] |
| knn | moving vs still | 0.651 | {1: 0.832, 2: 0.604, 3: 0.484} | [[366, 264], [70, 257]] |
| knn | empty vs occupied | 0.535 | {1: 0.548, 2: 0.508, 3: 0.552} | [[83, 227], [218, 429]] |
| knn | empty vs standing still | 0.248 | {1: 0.459, 2: 0.237, 3: 0.0} | [[122, 188], [286, 34]] |
| knn | 3-class | 0.378 | {1: 0.475, 2: 0.294, 3: 0.358} | [[84, 85, 141], [179, 18, 123], [45, 22, 260]] |
| random_forest | moving vs still | 0.454 | {1: 0.643, 2: 0.402, 3: 0.28} | [[267, 363], [160, 167]] |
| random_forest | empty vs occupied | 0.642 | {1: 0.603, 2: 0.661, 3: 0.667} | [[54, 256], [87, 560]] |
| random_forest | empty vs standing still | 0.37 | {1: 0.185, 2: 0.474, 3: 0.467} | [[206, 104], [293, 27]] |
| random_forest | 3-class | 0.338 | {1: 0.252, 2: 0.411, 3: 0.355} | [[61, 86, 163], [123, 9, 188], [58, 16, 253]] |

## Window ~5 s (their literal 64 samples, stride 8)

Windows per class: empty 59, standing 62, walking 64

| method | task | LOTO acc | per held-out trial | confusion (rows=true) |
|---|---|---|---|---|
| movement heuristic | moving vs still | 0.659 | {1: 0.632, 2: 0.708, 3: 0.635} | [[121, 0], [63, 1]] |
| knn | moving vs still | 0.892 | {1: 0.868, 2: 0.862, 3: 0.962} | [[110, 11], [9, 55]] |
| knn | empty vs occupied | 0.422 | {1: 0.515, 2: 0.369, 3: 0.365} | [[23, 36], [71, 55]] |
| knn | empty vs standing still | 0.207 | {1: 0.163, 2: 0.4, 3: 0.0} | [[25, 34], [62, 0]] |
| knn | 3-class | 0.427 | {1: 0.515, 2: 0.385, 3: 0.365} | [[24, 24, 11], [62, 0, 0], [9, 0, 55]] |
| random_forest | moving vs still | 0.93 | {1: 0.897, 2: 0.923, 3: 0.981} | [[116, 5], [8, 56]] |
| random_forest | empty vs occupied | 0.665 | {1: 0.691, 2: 0.631, 3: 0.673} | [[21, 38], [24, 102]] |
| random_forest | empty vs standing still | 0.479 | {1: 0.465, 2: 0.467, 3: 0.515} | [[38, 21], [42, 20]] |
| random_forest | 3-class | 0.622 | {1: 0.676, 2: 0.569, 3: 0.615} | [[30, 22, 7], [38, 22, 2], [1, 0, 63]] |
