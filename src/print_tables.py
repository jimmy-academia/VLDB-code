from pathlib import Path
from utils import *
import argparse

import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager

project_name_list = ['Axies', 'Bored Ape Yacht Club', 'Crypto Kitties', 'Fat Ape Club', 'Heterosis', 'Roaring Leader', 'StepN']


method_var_title = {
    'random': 'random',
    'proportion': 'popular',
    'greedy': 'greedy',
    'auction': 'auction',
    'main': 'BANTER',
}

thecolors = ['#FFD92F', '#2CA02C', '#FF7F0E', '#1F77B4', '#D62728']
num_methods = len(method_var_title.keys())

def struct_stack(name_list, n=num_methods):
    headpart = f'\\multirow{{{n}}}{{*}}{{\\shortstack{{'
    tailpart = '}}'
    return headpart+' '.join(name_list)+tailpart

project_var_title = {
    'Axies': struct_stack(['Axies', 'Infinity']),
    'BoredApeYachtClub': struct_stack(['Bored', 'Ape', 'Yacht', 'Club']),
    'CryptoKitties': struct_stack(['Crypto', 'Kitties']),
    'FatApeClub': struct_stack(['Fat', 'Ape', 'Club']),
    'Heterosis': struct_stack(['Heter', '-osis']),
    'RoaringLeader': struct_stack(['Roaring', 'Leader']),
    'StepN': struct_stack(['StepN']),
}

lastproject = list(project_var_title.keys())[-1]

def make_stats_table():
    print()
    for project_name in project_name_list:
        pname = ''.join(project_name.split())
        datafile = Path('data/small')/f'{pname}.json'
        infos = []
        if datafile.exists():
            nft_data = loadj(datafile)
            infos.append(len(nft_data['buyer_budgets']))
            infos.append(len(nft_data['asset_traits']))
            infos.append(sum(nft_data['item_counts']))
            infos.append(sum([len(options) for options in nft_data['trait_system'].values()]))
            infos.append(sum([len(assets) for assets in nft_data['buyer_assets']]))
            infos = map(lambda x: f'${x}$', infos)
        if project_name == 'Axies': project_name = 'Axies Infinity' 
        print('    '+project_name+' & '+' & '.join(infos)+' \\\\')
    print()


def readrow(project, method, isfirsttable=True):
    pair_cases = ['2+m']
    # pair_cases = ['none', '2', '2+m', '2+e', '2+f', '2+c', '3']
    additional_cases = None
    breed_cases = pair_cases if isfirsttable else additional_cases
    row_value_list = []

    for breed_var in breed_cases:
        result_json = Path('ckpt')/project/breed_var/f'{method}_result.json'
        result_pth = Path('ckpt')/project/breed_var/f'{method}_result.pth'
        if result_json.exists():
            result = loadj(result_json)
            total_sales = result['total'] 
            row_value_list.append(f'${total_sales:.2f}$')
            # row_value_list.append(f'${r_s:.2f}\\%$')
        else:
            row_value_list += ['']
    return ' & '.join(row_value_list) + '\\\\'


def make_first_table():
    print()
    for project, col1text in project_var_title.items():
        print('    '+col1text)
        for method, col2text in method_var_title.items():
            rowtext = f'& {col2text} & ' + readrow(project, method)
            print('    '+rowtext)
        print('    \\midrule') if project != lastproject else print('    \\bottomrule')
    print()


# ===========
# ===========
# ===========

def make_legend(legend_path='out/rev/legend.jpg', legends = method_var_title.values(), colors=thecolors):
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["font.size"] = 50
    plt.rcParams["font.weight"] = "bold"
    fig, ax = plt.subplots()
    for label, color in zip(legends, colors):
        ax.bar(0, 0, color=color, label=label)

    # Extract the handles and labels from the plot
    handles, labels = ax.get_legend_handles_labels()

    plt.close(fig)
    legend_fig_width = len(legends) * 1.5  # 1.5 inches per entry, adjust as needed
    fig_legend = plt.figure(figsize=(legend_fig_width, 1), dpi=300)  # High DPI for quality
    ax_legend = fig_legend.add_subplot(111)
    ax_legend.axis('off')
    ax_legend.legend(handles, labels, loc='center', ncol=len(legends), frameon=False, fontsize=50)
    fig_legend.savefig(legend_path, bbox_inches='tight')
    plt.close(fig_legend)

def make_plots(titles, rev_list, legends, path):
    # print(legends)
    # size = 24
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["font.size"] = 50
    plt.rcParams["font.weight"] = "bold"
    # plt.rcParams['xtick.labelsize'] = size
    plt.rcParams['ytick.labelsize'] = 40
    plt.figure(figsize=(8, 6), dpi=200)
    # plt.xlabel('Methods')

    plt.ylabel('Revenue')
    for i, (method, rev) in enumerate(zip(legends, rev_list)):
        plt.bar(method, rev, color=thecolors[i], label=method)
        # print(i, method, colors[i])
    # plt.bar(legends, rev_list, color=grey_shades)
    # plt.xticks(rotation=45)
    # plt.legend(loc='upper center', bbox_to_anchor=(0.45, 1.2), ncol=3, fontsize=27)
    # plt.subplots_adjust(top=.80, left=.17, right=.97, bottom=0.05, wspace=0.4)
    plt.xticks([])
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

   
def create_plot(cat = 0):
    print()
    bu = ['2+c', '3', '2+m']
    desc = ['homo', 'het', 'child']
    for project_name in project_name_list:
        pname =  'Axies' if 'Axies' in project_name else ''.join(project_name.split()) 
        project_revs = []
        for method in method_var_title:
            result_json = Path('ckpt')/pname/bu[cat]/f'{method}_result.json'
            revenue = loadj(result_json)['total']
            project_revs.append(revenue)
        print(pname, project_revs)
        make_plots(project_name_list, project_revs, method_var_title.values(), f'out/rev/{desc[cat]}_{pname}.jpg')
    print()

def first_plot():
    print('first_plot')
    create_plot(0)
def second_plot():
    print('second_plot')
    create_plot(1)
def third_plot():
    print('third_plot')
    create_plot(2)

def ablation_plot():
    print('ablation_plot')
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["font.size"] = 50
    plt.rcParams["font.weight"] = "bold"
    plt.rcParams['ytick.labelsize'] = 40

    result_dir = Path('out/abla')
    result_dir.mkdir(parents=True, exist_ok=True)
    
    bar_width = 0.2  # Width of each bar
    colors = ['#D62728',  # Red
          '#1F77B4',  # Sky Blue
          '#FF7F0E',  # Orange
          '#2CA02C',  # Bluish-green
          '#FFD92F',  # Yellow
          '#2171B5',  # Blue
          '#7F7F7F'] 
    labels = ['BANTER', 'BANTER (no init)', 'BANTER (no init and scheduling)']

    for i, project_name in enumerate(project_name_list):
        plt.figure(figsize=(8,6), dpi=200)
        
        pname = ''.join(project_name.split())
        for j, suf in enumerate(['', '2', '3']):
            method = 'main'+suf
            result_json = Path('ckpt')/pname/'2+m'/f'{method}_result.json'
            revenue = loadj(result_json)['total']
            plt.bar(bar_width*j, revenue, bar_width, label=labels[j], color=colors[j])        
        plt.ylabel('Revenue')
        plt.xticks([])
        plt.tight_layout()
        plt.savefig(result_dir/f'{pname}.jpg')
        plt.close()
    make_legend(result_dir/'legend.jpg', labels, colors[:3])
        
def main():
    parser = argparse.ArgumentParser(description="print table args")
    parser.add_argument("t", type=int, nargs='?', default=0)
    args = parser.parse_args()
    make_funcs = [make_stats_table, first_plot, second_plot, third_plot, ablation_plot, make_legend] #, third_plot
    match args.t:
        case 0|1|2|3|4|5:
            make_funcs[args.t]()
        case _:
            for func in make_funcs:
                func()

if __name__ == '__main__':
    main()