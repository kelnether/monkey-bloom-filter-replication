"""Geometric level sizes for the static benchmark and analytical model."""


def geometric_sizes(total, levels, ratio):
    """Exact total; integer rounding; reserve at least one key per level."""
    if levels < 1 or total < levels or ratio < 2:
        raise ValueError('Require total >= levels >= 1 and ratio >= 2')
    weights = [ratio ** level for level in range(levels)]
    remaining = total - levels
    exact = [remaining * w / sum(weights) for w in weights]
    sizes = [1 + int(x) for x in exact]
    order = sorted(range(levels), key=lambda i: exact[i] - int(exact[i]), reverse=True)
    for i in order[:total - sum(sizes)]:
        sizes[i] += 1
    return sizes
