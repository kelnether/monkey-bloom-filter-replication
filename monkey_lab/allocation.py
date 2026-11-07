"""Continuous KKT allocation plus byte rounding; not Appendix C transcription."""
import math

C = math.log(2) ** 2


def fpr(bits, entries):
    return math.exp(-C * bits / entries)


def allocate(sizes, budget_bytes, strategy='monkey'):
    if not sizes or any(type(n) is not int or n <= 0 for n in sizes):
        raise ValueError('sizes must be positive integers')
    if type(budget_bytes) is not int or budget_bytes < 0:
        raise ValueError('budget_bytes must be a nonnegative integer')
    if strategy not in ('uniform', 'monkey'):
        raise ValueError('unknown allocation strategy')
    if budget_bytes == 0:
        return [0] * len(sizes)
    if strategy == 'uniform':
        targets = [budget_bytes * n / sum(sizes) for n in sizes]
    else:
        # p_i = min(1, n_i*exp(-s)); m_i = n_i/C*max(0,s-ln(n_i)).
        lo = min(map(math.log, sizes))
        hi = max(map(math.log, sizes)) + C * 8 * budget_bytes / min(sizes) + 1
        for _ in range(100):
            s = (lo + hi) / 2
            used = sum(n / C * max(0, s - math.log(n)) for n in sizes)
            if used > 8 * budget_bytes:
                hi = s
            else:
                lo = s
        targets = [n / (8*C) * max(0, lo - math.log(n)) for n in sizes]
    result = [int(x) for x in targets]
    left = budget_bytes - sum(result)
    if strategy == 'uniform':
        order = sorted(range(len(sizes)), key=lambda i: targets[i]-result[i], reverse=True)
        for i in order[:left]:
            result[i] += 1
    else:
        for _ in range(left):
            i = max(range(len(sizes)), key=lambda i:
                    fpr(result[i]*8, sizes[i]) * -math.expm1(-8*C/sizes[i]))
            result[i] += 1
    assert sum(result) == budget_bytes
    return result


def model_sum(sizes, allocation):
    return sum(fpr(8*b, n) for n, b in zip(sizes, allocation))
