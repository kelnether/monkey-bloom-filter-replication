"""Reuse one dependency-free utility from the pinned upstream checkout."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'vendor/predictive-lsm-trees/lsm/utils.py'
spec = importlib.util.spec_from_file_location('_predictive_lsm_utils', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
calculate_level_capacity = module.calculate_level_capacity


def geometric_sizes(total, levels, ratio):
    """Exact total; integer rounding; reserve at least one key per level."""
    if levels < 1 or total < levels or ratio < 2:
        raise ValueError('Require total >= levels >= 1 and ratio >= 2')
    weights = [calculate_level_capacity(1, i, ratio) for i in range(levels)]
    remaining = total - levels
    exact = [remaining * w / sum(weights) for w in weights]
    sizes = [1 + int(x) for x in exact]
    order = sorted(range(levels), key=lambda i: exact[i] - int(exact[i]), reverse=True)
    for i in order[:total - sum(sizes)]:
        sizes[i] += 1
    return sizes
