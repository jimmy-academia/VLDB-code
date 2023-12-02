import argparse
from solver import return_solver, sell_result, NFTProject
from utils import *
from tqdm import tqdm

def prepare_args():
    parser = argparse.ArgumentParser(description="experiment args")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--N", type=int, default=None)
    parser.add_argument("--M", type=int, default=None)
    parser.add_argument("--nft_project", type=str, default='FatApeClub') #Axies
    parser.add_argument("--method", type=str, default='all') 
    parser.add_argument("--nft_sample_method", type=str, default='data') 
    parser.add_argument("--user_pref_method", type=str, default='data') 
    parser.add_argument("--user_budget_method", type=str, default='data') 
    parser.add_argument("--nft_count_method", type=str, default='data') 
    parser.add_argument("--max_budget", type=int, default=100)
    parser.add_argument("--max_nft_count", type=int, default=5)
    parser.add_argument("--user_iters", type=int, default=128) 
    parser.add_argument("--n_iters", type=int, default=128) 
    parser.add_argument("--auction_iters", type=int, default=32) 
    parser.add_argument("--auction_init", type=int, default=1) 
    parser.add_argument("--user_eps", type=float, default=1e-4)
    parser.add_argument("--eps", type=float, default=1000)
    parser.add_argument("--decay", type=float, default=0.9)
    parser.add_argument("--div", type=int, default=7)
    parser.add_argument("--gamma", type=float, default=1000)
    parser.add_argument("--breeding_topk", type=str, default=20) 
    parser.add_argument("--breeding_util", '-bu', type=str, default='2+m') 
    parser.add_argument("--mutation_samples", type=int, default=64)
    parser.add_argument("--mutation_rate", type=float, default=0.05)
    parser.add_argument("--rare_ratio", type=float, default=0.05)
    parser.add_argument("--ctopk", type=float, default=10)
    parser.add_argument("--rerun", type=str, default=False)
    parser.add_argument("--ckpt_dir", type=str, default='ckpt')
    parser.add_argument("--dset_dir", type=str, default='data/small')
    args = parser.parse_args()
    return args

def main(bu=None, project=None):
    args = prepare_args()
    set_seeds(args.seed)

    check_valve = False
    if bu is not None:
        args.breeding_util = bu
        check_valve=True
    if project is not None:
        args.nft_project = project
        check_valve = True
    
    [args.ckpt_dir, args.dset_dir] = map(Path, [args.ckpt_dir, args.dset_dir])
    args.cache_dir = args.ckpt_dir/args.nft_project
    args.ckpt_dir = args.ckpt_dir/args.nft_project/args.breeding_util
    args.ckpt_dir.mkdir(parents=True, exist_ok=True)
    args.device = torch.device("cpu" if args.device == -1 else "cuda:"+str(args.device))

    if args.nft_project == 'StepN': args.eps = 100
    if args.nft_project == 'Heterosis': args.eps = 50
    if not (args.dset_dir/f'{args.nft_project}.json').exists(): input('No data!')
    if args.method == 'all':
        for method in ['main', 'greedy', 'random', 'proportion', 'auction']:
            args.method = method
            args.result_file = args.ckpt_dir/f'{args.method}_result.json'
            args.result_pth = args.ckpt_dir/f'{args.method}_result.pth'
            if check_valve and args.result_file.exists(): continue
            if args.result_file.exists() and not args.rerun: args.rerun=ask_proceed()
            operate(args)
    else:
        args.result_file = args.ckpt_dir/f'{args.method}_result.json'
        args.result_pth = args.ckpt_dir/f'{args.method}_result.pth'
        if args.result_file.exists() and not args.rerun: ask_proceed()
        operate(args)

    if not check_valve:
        print()
        for method in ['random', 'greedy', 'proportion', 'auction', 'main']:
            rjson = args.ckpt_dir/f'{method}_result.json'
            if rjson.exists():
                result = loadj(rjson)
                print(method, result['total'])
            else:
                print(method, '--')
    

def operate(args):
    print('=== === === === === === ===')
    print(f'Solving nft_project {args.nft_project} with breeding util {args.breeding_util} by {args.method}')
    print('=== === === === === === ===')
    nft_project = NFTProject(args)
    args = nft_project.first_load(args.M)
    Solver = return_solver(args, nft_project)
    Solver.solve()
    prices = Solver.final_prices.to(args.device)
    demand = Solver.solve_user_demand(prices)
    sell_result(args, demand, Solver.budget, nft_project.item_count, prices)

if __name__ == "__main__":
    main()
    