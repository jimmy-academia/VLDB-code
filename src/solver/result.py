from math import floor
import random
import torch
from tqdm import tqdm
from utils import *

def sell_result(args, demand, budget, item_count, prices, save=True):
    if save:
        rpth = [args, demand.cpu(), budget.cpu(), item_count, prices.cpu()]
        torch.save(rpth, args.result_pth)

    item_count = torch.LongTensor(item_count).to(args.device)
    excess = (demand.sum() - item_count.sum())/item_count.sum()
    if not all((demand*prices).sum(1)<= budget):
        demand *= budget/(demand*prices).sum(1)
    total_demand = demand.sum(0)
    amount = torch.where(total_demand > item_count, item_count, total_demand)
    Revenue = (amount*prices).sum()

    print('total sales:', Revenue)
    print('excess:', excess)
    result = {
        'total': float(Revenue),
        'excess': float(excess)
    }
    dumpj(result, args.result_file)
    
if __name__ == '__main__':
    print('hello')