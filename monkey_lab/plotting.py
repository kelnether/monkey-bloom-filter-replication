"""Standalone PNG/SVG scientific plots and a static HTML results report."""
import csv
import html
import json
from pathlib import Path


def make_report(directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    directory = Path(directory)
    config = json.loads((directory/'config.json').read_text())
    base = config['experiment']
    with (directory/'summary.csv').open() as f:
        rows = list(csv.DictReader(f))
    best = json.loads((directory/'best_configs.json').read_text())
    figures = directory/'figures'
    figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False,
                         'axes.titleweight':'bold','figure.facecolor':'#f8fafc','axes.facecolor':'white'})
    colors = {'uniform':'#64748b','monkey':'#087e8b'}
    model_colors = colors.copy()
    if config.get('include_appendix_c'):
        colors['monkey_appendix_c'] = '#b65324'

    def select(strategy, variable):
        dimensions = ['entries','levels','ratio','bits_per_key','requested_miss_fraction']
        if 'queries' in rows[0]:
            dimensions.append('queries')
        return sorted([r for r in rows if r['strategy']==strategy and all(
            float(r[k])==base['miss_fraction' if k=='requested_miss_fraction' else k]
            for k in dimensions if k!=variable)], key=lambda r: float(r[variable]))

    def plot_accesses(ax, variable, title, xlabel):
        for strategy, color in colors.items():
            subset = select(strategy, variable)
            appendix_c = strategy == 'monkey_appendix_c'
            ax.errorbar([float(r[variable]) for r in subset],
                        [float(r['measured_blocks_mean']) for r in subset],
                        yerr=[float(r['measured_blocks_sd']) for r in subset],
                        marker='s' if appendix_c else 'o',
                        linestyle='--' if appendix_c else '-',
                        markerfacecolor='none' if appendix_c else color,
                        capsize=4, color=color, label=strategy)
        ax.set(title=title, xlabel=xlabel, ylabel='Logical block accesses / query')
        ax.grid(alpha=.2)
        ax.legend()

    fig, axes = plt.subplots(1,3,figsize=(15,4.6),layout='constrained')
    for ax, variable, title, xlabel in zip(axes,
            ['bits_per_key','ratio','requested_miss_fraction'],
            ['A | Filter memory budget','B | Level-size ratio','C | Unsuccessful lookups'],
            ['Average filter bits / key','Level-size ratio T','Fraction of unsuccessful lookups']):
        plot_accesses(ax, variable, title, xlabel)
        if variable=='bits_per_key':
            ax.set_yscale('symlog',linthresh=.02)
    fig.suptitle('Monkey static replication | measured means +/- one sample SD',fontsize=15)
    for suffix in ('png','svg'):
        fig.savefig(figures/f'benchmarks.{suffix}',dpi=160)
    plt.close(fig)

    def save_access_chart(variable, title, xlabel, filename):
        ticks = [int(row[variable]) for row in select('uniform', variable)]
        if len(ticks) < 2:
            return False
        fig, ax = plt.subplots(figsize=(7.5, 4.8), layout='constrained')
        plot_accesses(ax, variable, title, xlabel)
        ax.set(xticks=ticks, ylim=(0, None))
        for suffix in ('png', 'svg'):
            fig.savefig(figures/f'{filename}.{suffix}', dpi=160)
        plt.close(fig)
        return True

    level_section = ''
    if save_access_chart('levels', 'Effect of number of levels', 'Number of levels', 'level_count'):
        level_section = (
            '<h2>Effect of level count</h2>'
            f'<p>The sweep varies the number of levels while holding the key count at {base["entries"]:,}, '
            f'the level-size ratio at T={base["ratio"]}, the budget at '
            f'{base["bits_per_key"]} bits per key, and the miss fraction at {base["miss_fraction"]:.0%}. '
            'Points are cross-seed means. Error bars show one sample standard deviation.</p>'
            '<img class="half" src="figures/level_count.png" alt="Mean logical page accesses by strategy and level count">'
        )

    query_section = ''
    if 'queries' in rows[0] and save_access_chart(
            'queries', 'Fixed data | effect of query count', 'Unsuccessful queries per seed', 'query_count'):
        query_section = (
            '<h2>Query-count comparison on fixed data</h2>'
            '<p>Within each seed, the keys, level layout, and hash salts are fixed. The shorter query sequence is a prefix of the full sequence. '
            'Error bars show one sample standard deviation across seeds.</p>'
            '<img class="half" src="figures/query_count.png" alt="Mean logical page accesses by query count on fixed data">'
        )

    fig,ax = plt.subplots(figsize=(7.5,4.8),layout='constrained')
    for strategy in colors:
        subset = select(strategy, 'bits_per_key')
        x = [float(r['bits_per_key']) for r in subset]
        ax.plot(x,[float(r['measured_absent_blocks_mean']) for r in subset],'o-',color=colors[strategy],label=f'{strategy}: measured')
        ax.plot(x,[float(r['integer_k_absent_model_mean']) for r in subset],'--',color=colors[strategy],label=f'{strategy}: integer-k model')
    ax.set(title='Model check | absent keys',xlabel='Average filter bits / key',
           ylabel='Logical block accesses / absent query',yscale='symlog')
    ax.set_yscale('symlog',linthresh=.02)
    ax.grid(alpha=.2); ax.legend()
    for suffix in ('png','svg'):
        fig.savefig(figures/f'model_check.{suffix}',dpi=160)
    plt.close(fig)

    fig,ax = plt.subplots(figsize=(7.5,4.8),layout='constrained')
    for strategy in model_colors:
        subset = sorted([r for r in best if r['strategy']==strategy],key=lambda r:r['write_fraction'])
        ax.plot([r['write_fraction'] for r in subset],[r['theta'] for r in subset],
                'o-',color=colors[strategy],label=f'{strategy}: best in grid')
    ax.set(title='Parameter search | analytical prediction only',xlabel='Write fraction',
           ylabel='Predicted weighted I/O cost per operation')
    ax.legend(); ax.grid(alpha=.2)
    for suffix in ('png','svg'):
        fig.savefig(figures/f'parameter_search.{suffix}',dpi=160)
    plt.close(fig)

    base_rows = {s:next(r for r in select(s,'bits_per_key') if float(r['bits_per_key'])==base['bits_per_key']) for s in colors}
    baseline=float(base_rows['uniform']['measured_blocks_mean'])
    optimized=float(base_rows['monkey']['measured_blocks_mean'])
    improvement=(baseline-optimized)/baseline if baseline else 0
    table=''.join('<tr>'+''.join(f'<td>{html.escape(str(r[k]) if k!="theta" else f"{r[k]:.4f}")}</td>'
                                for k in ['write_fraction','strategy','policy','ratio','buffer_fraction','levels','theta'])+'</tr>' for r in best)
    report=f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Monkey experiment report</title>
<style>body{{font:16px/1.7 -apple-system,BlinkMacSystemFont,sans-serif;color:#17283c;background:#f8fafc;margin:0}}main{{max-width:1120px;margin:auto;padding:36px 24px}}h1{{font-size:34px;margin-bottom:8px}}h2{{margin-top:32px}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card{{background:white;border:1px solid #dce4ed;border-radius:12px;padding:18px;flex:1;min-width:180px}}strong.number{{display:block;font-size:30px;color:#087e8b}}img{{width:100%;background:white;border-radius:12px}}.half{{max-width:750px}}table{{border-collapse:collapse;background:white;width:100%}}th,td{{padding:9px;border-bottom:1px solid #dce4ed;text-align:left}}.scroll{{overflow:auto}}a{{color:#087e8b}}.note{{border-left:4px solid #087e8b;padding:12px 18px;background:#eaf5f5}}code{{background:#e8edf2;padding:2px 5px}}</style>
<main><p>DSC5003 · Python replication</p><h1>Monkey filter allocation under a fixed memory budget</h1>
<p>Packed Bloom filters · Static levels · Paired experiments · Analytical parameter search</p>
<div class="cards"><div class="card">Uniform allocation<strong class="number">{baseline:.5f}</strong>logical page accesses per query</div>
<div class="card">Monkey allocation<strong class="number">{optimized:.5f}</strong>logical page accesses per query</div>
<div class="card">Base-case reduction<strong class="number">{improvement:.1%}</strong>relative to uniform bits per key</div></div>
<p>Base case with {base['entries']:,} keys, {base['levels']} levels, T={base['ratio']}, {base['bits_per_key']} bits per key, {base['queries']:,} queries per seed, and a miss fraction of {base['miss_fraction']:.0%}. Seeds used were {html.escape(str(config['seeds']))}.</p>
<p class="note">The experiments run real Bloom filters on static data in memory. Measurements cover logical page accesses and filter bytearray payload. The parameter search uses analytical costs. The monkey strategy solves the continuous objective by bisection. When enabled, monkey_appendix_c uses the iterative transfers described in Appendix C.</p>
<h2>Paired experiments</h2><p>Within each seed, strategies share data, queries, hash salts, and total filter budget. Error bars show one sample standard deviation across seeds.</p><img src="figures/benchmarks.png" alt="Measured page accesses across filter budgets, level-size ratios, and miss fractions">
{level_section}
{query_section}
<h2>Measurements and model predictions</h2><p>The measured miss cost sums per-level false-positive rates over the full set of absent keys. Mixed workloads draw their misses from that set. The CSV includes both the integer-hash-count and continuous models.</p><img class="half" src="figures/model_check.png" alt="Measured and predicted page accesses">
<h2>Analytical parameter search</h2><p>The grid enumerates merge policies, level-size ratios, and buffer shares. It reports the lowest predicted weighted cost among those candidates. The tuning budget covers the buffer and filters. A successful lookup is modeled at the deepest run.</p><img class="half" src="figures/parameter_search.png" alt="Lowest predicted cost on the grid by write fraction">
<div class="scroll"><table><tr><th>Write fraction</th><th>Allocation</th><th>Merge policy</th><th>T</th><th>Buffer share</th><th>Levels</th><th>Predicted cost</th></tr>{table}</table></div>
<h2>Data and sources</h2><p><a href="experiments.csv">Per-run measurements</a> · <a href="levels.csv">Per-level filter data</a> · <a href="summary.csv">Means and standard deviations</a> · <a href="model_search.csv">Analytical candidates</a> · <a href="config.json">Configuration</a> · <a href="metadata.json">Environment and source hashes</a></p>
<p>Based on Monkey (SIGMOD 2017). <a href="https://github.com/fiidalgo/predictive-lsm-trees">predictive-lsm-trees</a> informed the BloomFilter interface and Run and Level organization. See THIRD_PARTY.md for attribution and the provenance of archived results.</p></main></html>'''
    (directory/'report.html').write_text(report,encoding='utf-8')
    return directory/'report.html'
