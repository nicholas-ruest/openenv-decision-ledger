"""Isolated merge-contract witnesses; distractors cannot bridge the boundary."""


def inputs(rng, count):
    for index in range(count):
        origin, width = rng.randint(-10000, 10000), rng.randint(3, 12)
        mode = index % 6
        if mode == 0:  # Nested interval, no touching boundary.
            pairs, touching = [[0, 4 * width], [width, 2 * width]], False
        elif mode == 1:  # Touching-only pair which must remain separate.
            pairs, touching = [[0, width], [width, 3 * width]], False
        elif mode == 2:  # Both faults; fixing only one still leaves a wrong answer.
            pairs, touching = [[0, 4 * width], [width, 2 * width], [4 * width, 5 * width]], False
        elif mode == 3:  # Positive control: touching is explicitly enabled.
            pairs, touching = [[0, width], [width, 3 * width]], True
        elif mode == 4:  # Rejections and disjoint intervals, with no seeded fault active.
            pairs, touching = [[3 * width, 2 * width], [5 * width, 5 * width], [0, width]], False
        else:  # Duplicate outer interval followed by a strict nested interval.
            pairs, touching = [[0, 4 * width], [0, 4 * width], [width, 2 * width]], True
        pairs = [[origin + lo, origin + hi] for lo, hi in pairs]
        # Match merge-d2's 11 pairs. Keep positive/negative examples intact:
        # random wide distractors could otherwise connect the touching boundary.
        for number in range(11 - len(pairs)):
            lo = origin + (50 + 3 * number) * width
            pairs.append([lo, lo + rng.randint(1, width)])
        rng.shuffle(pairs)
        yield [pairs, touching]
