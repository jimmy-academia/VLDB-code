from .grad import MainMarketSolver, GreedySolver, AuctionSolver
from .base import BaseSolver
from .result import sell_result
from .project import NFTProject

def return_solver(args, nft_project, buyer_types=None):
    if 'main' in args.method:
        return MainMarketSolver(args, nft_project, buyer_types)
    match args.method:
        case 'random' | 'proportion':
            return BaseSolver(args, nft_project)
        case 'greedy':
            return GreedySolver(args, nft_project)
        case 'auction':
            return AuctionSolver(args, nft_project)
        case _:
            print(f'Not Implemented: args.method = {args.method}')
            input()
