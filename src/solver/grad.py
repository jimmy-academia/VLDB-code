from .base import BaseSolver

import torch
import random
from tqdm import tqdm
from utils import *

# 'main', 'main2' (no greedy init), 'main3' (no greedy init and no scheduling)

class MainMarketSolver(BaseSolver):
    def __init__(self, args, nft_project, buyer_types=None):
        super().__init__(args, nft_project, buyer_types)

    def solve(self):
        init = 'o'
        if len(self.args.method.split('_'))>1:
            init = self.args.method.split('_')[1]
        match init:
            case 'a':
                prices = torch.load(self.args.ckpt_dir/'auction_result.pth')[4].to(self.args.device)
            case 'g':
                prices = torch.load(self.args.ckpt_dir/'greedy_result.pth')[4].to(self.args.device)
            case 'r':
                prices = self.random_propotional_prices()
            case 'p':
                prices = self.random_propotional_prices(False)
            case _:
                prices = self.random_propotional_prices()
                for k in range(self.args.div):
                    total_spending = 0
                    for i in range(self.args.N):
                        budget = self.nftP.user_budgets[i] 
                        spending = self.Uij[i].clone() 
                        spending = spending / prices
                        spending = spending/spending.sum()
                        total_spending += spending * budget
                    prices = total_spending/torch.LongTensor(self.nftP.item_count).to(self.args.device)
                    
        item_count = torch.Tensor(self.nftP.item_count).to(self.args.device)
        pbar = tqdm(range(self.args.n_iters), ncols=88, desc='main_solve')
        list_excess = []
        list_rev = []
        for it in pbar:
            demand = self.solve_user_demand(prices)
            demand = demand.sum(0)
            excess = demand - item_count
            old_prices = prices.clone()
            prices *= ( 1 +  self.args.eps * excess/(excess.abs().sum()))
            prices = torch.where(prices < 1e-10, 1e-10, prices) 
            pbar.set_postfix(excess=float(excess.sum()))
            if '3' not in self.args.method:
                self.args.eps *= self.args.decay

        self.final_prices = prices 

class GreedySolver(BaseSolver):
    def __init__(self, args, nft_project):
        super().__init__(args, nft_project)

    def solve(self):
        prices = self.random_propotional_prices()
        for k in range(self.args.div):
            total_spending = 0
            for i in range(self.args.N):
                budget = self.nftP.user_budgets[i] 
                spending = self.Uij[i].clone() 
                spending = spending / prices
                spending = spending/spending.sum()
                total_spending += spending * budget
            prices = total_spending/torch.LongTensor(self.nftP.item_count).to(self.args.device)
        self.final_prices = prices

class AuctionSolver(BaseSolver):
    def __init__(self, args, nft_project):
        super().__init__(args, nft_project)

    def solve(self):
        prices = [0.5]*self.args.M
        prices = torch.Tensor(prices).to(self.args.device)
        remain_budgets = torch.Tensor(self.nftP.user_budgets[:]).to(self.args.device)
        x,h,l = map(lambda x: torch.zeros(self.args.N, self.args.M).to(self.args.device), range(3))
        a = torch.Tensor(self.nftP.item_count[:]).to(self.args.device)
        eps = 0.1
        pbar = tqdm(range(self.args.auction_iters), ncols=88, desc='auction solve')
        for __ in pbar:
            random_id_list = random.sample(range(self.args.N), self.args.N)
            for i in random_id_list:
                budget = remain_budgets[i]
                if budget > 0:
                    j = torch.argmax(self.Uij[i]/prices)
                    if self.Uij[i][j] <= prices[j]:
                        break
                    if a[j] != 0:
                        amount = min(a[j], budget/prices[j])
                        a[j] -= amount
                        x[i][j] += amount
                        h[i][j] += amount
                        remain_budgets[i] -= amount*prices[j]
                    elif l.sum(0)[j] > 0:
                        candidate = [i for i in range(args.N) if (l[:, j]>0)[i]]
                        c = random.choice(candidate)
                        amount = min(l[c][j], budget/prices[j])
                        l[c][j] -= amount
                        x[c][j] -= amount
                        remain_budgets[c] += amount*prices[j]
                        h[i][j] += amount
                        x[i][j] += amount
                        remain_budgets[i] -= amount*prices[j]*(1+eps)
                    else:
                        h[:, j] = l[:, j]
                        remain_budgets -= h[:, j]*eps
                        l[:, j] = 0
                        prices[j] *= (1+eps)

            if all(remain_budgets < min(prices)): break

        self.final_prices = prices


