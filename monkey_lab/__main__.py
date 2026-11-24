import argparse
from pathlib import Path
from .experiments import run_all


def main():
    parser = argparse.ArgumentParser(description='Static Monkey experiment lab')
    sub = parser.add_subparsers(dest='command',required=True)
    run = sub.add_parser('run',help='run paired experiments and model grid search')
    run.add_argument('--config',type=Path,default=Path('configs/default.json'))
    run.add_argument('--out', type=Path, required=True, help='new or empty results directory')
    run.add_argument('--no-plots',action='store_true')
    plot = sub.add_parser('plot',help='plot existing results without rerunning experiments')
    plot.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='run':
        run_all(args.config,args.out)
        if args.no_plots:
            print(f'Results: {args.out.resolve()}')
            return
    from .plotting import make_report
    print(f'Report: {make_report(args.out).resolve()}')


if __name__=='__main__':
    main()
