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

    def select(strategy, variable):
        dimensions = ['entries','levels','ratio','bits_per_key','requested_miss_fraction']
        return sorted([r for r in rows if r['strategy']==strategy and all(
            float(r[k])==base['miss_fraction' if k=='requested_miss_fraction' else k]
            for k in dimensions if k!=variable)], key=lambda r: float(r[variable]))

    fig, axes = plt.subplots(1,3,figsize=(15,4.6),layout='constrained')
    for ax, variable, title, xlabel in zip(axes,
            ['bits_per_key','ratio','requested_miss_fraction'],
            ['A | Filter memory budget','B | Level-size ratio','C | Unsuccessful lookups'],
            ['Average filter bits / key','Level-size ratio T','Fraction of unsuccessful lookups']):
        for strategy in colors:
            subset = select(strategy, variable)
            ax.errorbar([float(r[variable]) for r in subset],
                        [float(r['measured_blocks_mean']) for r in subset],
                        yerr=[float(r['measured_blocks_sd']) for r in subset],
                        marker='o',capsize=4,color=colors[strategy],label=strategy)
        ax.set(title=title,xlabel=xlabel,ylabel='Logical block accesses / query')
        ax.grid(alpha=.2)
        ax.legend()
        if variable=='bits_per_key':
            ax.set_yscale('symlog',linthresh=.02)
    fig.suptitle('Monkey static replication | measured means +/- one sample SD',fontsize=15)
    for suffix in ('png','svg'):
        fig.savefig(figures/f'benchmarks.{suffix}',dpi=160)
    plt.close(fig)

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
    for strategy in colors:
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
    report=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Monkey 实验报告</title>
<style>body{{font:16px/1.7 -apple-system,BlinkMacSystemFont,sans-serif;color:#17283c;background:#f8fafc;margin:0}}main{{max-width:1120px;margin:auto;padding:36px 24px}}h1{{font-size:34px;margin-bottom:8px}}h2{{margin-top:32px}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card{{background:white;border:1px solid #dce4ed;border-radius:12px;padding:18px;flex:1;min-width:180px}}strong.number{{display:block;font-size:30px;color:#087e8b}}img{{width:100%;background:white;border-radius:12px}}.half{{max-width:750px}}table{{border-collapse:collapse;background:white;width:100%}}th,td{{padding:9px;border-bottom:1px solid #dce4ed;text-align:left}}.scroll{{overflow:auto}}a{{color:#087e8b}}.note{{border-left:4px solid #087e8b;padding:12px 18px;background:#eaf5f5}}code{{background:#e8edf2;padding:2px 5px}}</style>
<main><p>DSC5003 · Python / macOS · 最小可行系统</p><h1>Monkey：固定内存预算下的过滤器分配</h1>
<p>真实 Bloom filter · 静态多层数据 · 可重现对照实验 · 成本模型参数搜索</p>
<div class="cards"><div class="card">基线平均访问<strong class="number">{baseline:.5f}</strong>逻辑数据块 / 查询</div>
<div class="card">Monkey 平均访问<strong class="number">{optimized:.5f}</strong>逻辑数据块 / 查询</div>
<div class="card">本次基础场景减少<strong class="number">{improvement:.1%}</strong>相对统一 bits/key</div></div>
<p>基础场景：{base['entries']:,} 个键，{base['levels']} 层，T={base['ratio']}，平均 {base['bits_per_key']} bits/key，未命中比例 {base['miss_fraction']:.0%}。随机种子：{html.escape(str(config['seeds']))}。</p>
<p class="note">实测对象为内存中的静态数据布局和真实过滤器。逻辑块访问不是物理磁盘 I/O；位数组载荷不是进程总内存。参数搜索结果来自理论模型，没有实测 compaction 或系统吞吐量。当前分配器求解论文连续优化目标，不是附录 C 的逐行实现。</p>
<h2>对照实验</h2><p>每个种子的两种策略共享数据、查询、哈希盐和总过滤器预算。误差线为跨种子的样本标准差。</p><img src="figures/benchmarks.png" alt="不同内存预算、层级比例和未命中率下的实测访问次数">
<h2>理论与实测核对</h2><p>独立未命中探测集用于测量各层误报率，再求和。整数哈希数量模型与连续分配模型分别保存在 CSV 中。</p><img class="half" src="figures/model_check.png" alt="模型与实测比较">
<h2>参数搜索：仅模型预测</h2><p>枚举合并策略、T 和缓冲区比例；展示给定网格内的最低加权成本。不是全设计空间的最优性证明。调优内存预算仅包含 buffer 和 filters；命中成本按最深 run 的保守位置估计。</p><img class="half" src="figures/parameter_search.png" alt="不同写比例下的理论最优网格配置">
<div class="scroll"><table><tr><th>写比例</th><th>分配</th><th>合并策略</th><th>T</th><th>缓冲区比例</th><th>层数</th><th>预测成本</th></tr>{table}</table></div>
<h2>数据与来源</h2><p><a href="experiments.csv">逐次实验 CSV</a> · <a href="levels.csv">逐层过滤器 CSV</a> · <a href="summary.csv">均值与标准差</a> · <a href="model_search.csv">全部模型候选</a> · <a href="config.json">配置</a> · <a href="metadata.json">环境和代码指纹</a></p>
<p>依据 Monkey（SIGMOD 2017），参考并改造 <a href="https://github.com/fiidalgo/predictive-lsm-trees">predictive-lsm-trees</a> 的 BloomFilter / Run / Level 组织方式，并直接复用其层容量工具函数。源码归属与改动见项目 THIRD_PARTY.md。</p></main></html>'''
    (directory/'report.html').write_text(report,encoding='utf-8')
    return directory/'report.html'
