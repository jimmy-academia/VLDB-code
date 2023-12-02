from pathlib import Path
from statistics import mean
from utils import *
import torch
from solver import return_solver, NFTProject
import matplotlib.pyplot as plt
from tqdm import tqdm

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 50
plt.rcParams["font.weight"] = "bold"
plt.rcParams['xtick.labelsize'] = 40
plt.rcParams['ytick.labelsize'] = 40

nft_projects_name = ['BoredApeYachtClub', 'FatApeClub', 'StepN']
device = torch.device("cuda:0")

def main():
    for pp, project in enumerate(nft_projects_name):
        print('equilibrium plot for project', project)

        result_dir = Path('out/cache_equi')
        jpg_dir = Path('out/equi')
        if not result_dir.exists(): result_dir.mkdir()
        if not jpg_dir.exists(): jpg_dir.mkdir()
        result_path = result_dir/f'{project}_result.json'
        if not result_path.exists():
            args, demand, budget, item_count, prices = torch.load(f'ckpt/{project}/2+m/main_result.pth', map_location=device)

            args.device = device
            nft_project = NFTProject(args)
            args = nft_project.first_load()
            args.user_eps = 1e-4
            Solver = return_solver(args, nft_project)

            item_count = torch.LongTensor(item_count).to(args.device)
            prices = prices.to(args.device)
            minimum_price = 1e-6

            X = []
            Y = []
            for i in tqdm(range(-10, 11), ncols=88, desc='equi tests..'):
                repeat = 1
                X.append(i)
                y_list = []                
                for __ in range(repeat):
                    newprice = prices.clone()
                    newprice *= (1+0.01*i)
                    newprice = torch.where(newprice > minimum_price, newprice, minimum_price)
                    demand = Solver.solve_user_demand(newprice)
                    demand = demand.sum(0)
                    excess = demand - item_count
                    y_list.append(excess.norm().cpu().item())
                    print(i, excess.norm().cpu().item())
                Y.append(y_list)
            dumpj([X, Y], result_path)
        else:        
            X, Y = loadj(result_path)
        y_means = []
        for y_list in Y:
            y_means.append(mean(y_list))

        plt.figure(figsize=(8, 8), dpi=300)
        plt.xlabel('Deviation Level')
        plt.ylabel('Total Excess Demand')
        plt.plot(X, y_means, color='black')
        plt.xlim(min(X)-0.1, max(X)+0.1)
        plt.tight_layout()
        plt.savefig(jpg_dir/f'{project}.jpg')
        plt.close()



if __name__ == '__main__':
    main()
