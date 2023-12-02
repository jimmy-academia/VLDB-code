from pathlib import Path
import torch
from solver import return_solver, NFTProject
import matplotlib.pyplot as plt
from tqdm import tqdm
import time
from utils import *
from statistics import mean

nft_projects_name = ['FatApeClub', 'Heterosis'] 

def main():
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["font.size"] = 50
    plt.rcParams["font.weight"] = "bold"
    plt.rcParams['xtick.labelsize'] = 40
    plt.rcParams['ytick.labelsize'] = 40

    for bu in ['2+m', '3']:
        for project in nft_projects_name:
            print('runtime test for project', project)

            result_dir = Path('out/time')
            if not result_dir.exists(): result_dir.mkdir(parents=True)
            result_path = result_dir/f'{project}_{bu[0]}_result.pth'
            if not result_path.exists():
                device = torch.device("cuda:0")
                args, demand, budget, item_count, prices = torch.load(f'best/{project}/{bu}/main_result.pth', map_location=device)

                nft_project = NFTProject(args)
                args = nft_project.first_load()
                args.user_eps = 1e-4
                args.device = device
                Solver = return_solver(args, nft_project)
                X = []
                Y = []
                for ctopk in tqdm(range(5, 15), ncols=88, desc='runtime tests..'):
                    lenC = ctopk * (ctopk+1)//2
                    Solver.args.ctopk = ctopk
                    repeat = 3
                    for __ in range(repeat):
                        start = time.time()
                        Solver.prepare_top_pairs()
                        end = time.time()
                        X.append(lenC)
                        Y.append(end-start)
                torch.save([X, Y], result_path)
            else:        
                X, Y = torch.load(result_path)
                y_list = [Y[i*3:(i+1)*3] for i in range(len(Y)//3)]
                y_list = [mean(y) for y in y_list]
                plt.figure(figsize=(6, 8), dpi=300)
                plt.xlabel(r'$|C|$')
                plt.ylabel('Run Time (s)')
                plt.plot(X[::3], y_list, color='black')
                plt.tight_layout()
                plt.savefig(result_dir/f'{project}{bu[0]}.jpg')
                plt.close()
            

if __name__ == '__main__':
    main()
