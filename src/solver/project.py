import random
from pathlib import Path
from utils import *
import heapq


class NFTProject:
    def __init__(self, args=None, first_init=True, **kwargs):
        if first_init:
            self.args = args
            self.data = self.load_data()
            self.trait_dict = self.data['trait_system']
            self.args.T = len(self.trait_dict)

        else:
            self.__dict__.update(kwargs)

    def to_json(self):        
        return self.__dict__

    @classmethod
    def from_json(cls, json_data):
        return cls(first_init=False, **json_data)

    def load_data(self):
        data = loadj(self.args.dset_dir / (self.args.nft_project + '.json'))
        return data

    def first_load(self, setM=None):
        self.args.N = len(self.data['buyer_budgets'])
        self.args.M = len(self.data['asset_traits'])

        if setM is not None:
            self.args.M = setM

        self.item_list = self.sample_items()
        
        self.item_vec_list = self.item_trait_vectorize()
        self.trait_counts = self.compute_trait_stats()
        self.item_count = self.get_item_counts()
        self.user_preferences = self.get_user_preferences()
        self.user_budgets = self.get_user_budgets()
        self.prep_trait_options_info()
        return self.args

    def sample_items(self):
        if self.args.nft_sample_method == 'random':
            return random.sample(self.data['asset_traits'], self.args.M)
        elif self.args.nft_sample_method == 'data':
            return self.data['asset_traits']
        else:
            print(f'Not Implemented: args.nft_sample_method = {self.args.nft_sample_method}')
            input()

    def item_trait_vectorize(self):
        new_list = []
        for item in self.item_list:
            item_vec = []
            for (trait, options), choice in zip(self.trait_dict.items(), item):
                item_vec.append(options.index(choice))
            new_list.append(item_vec)
        return new_list

    def compute_trait_stats(self):
        trait_counts = []
        for trait, options in self.trait_dict.items():
            trait_counts.append([1 for __ in options])
        for item_vec in self.item_vec_list:
            for t, choice in enumerate(item_vec):
                trait_counts[t][choice] += 1
        return trait_counts

    def get_item_counts(self):
        match self.args.nft_count_method:
            case 'data':
                return self.data['item_counts']
            case 'rand_gen':
                return rand_gen_counts(self.args)
            case 'one':
                return [1]*len(self.data['item_counts'])
            case _:
                print(f'Not Implemented: args.nft_count_method = {self.args.nft_count_method}')

    def get_user_preferences(self):
        match self.args.user_pref_method:
            case 'data':
                user_preferences = []
                for __ in range(self.args.N):
                    user_pref = []
                    for trait, options in self.trait_dict.items():
                        user_pref.append([0 for option in options])
                    user_preferences.append(user_pref)
                for i in range(self.args.N):
                    asset_list = self.data['buyer_assets'][i]
                    for asset in asset_list:
                        for t, (trait, options) in enumerate(self.trait_dict.items()):
                            user_preferences[i][t][options.index(asset[t])] +=1
                return user_preferences
            case 'rand_gen':
                return rand_gen_preferences(self.args, self.trait_dict)
            case 'one':
                return rand_gen_preferences(self.args, self.trait_dict, True)

            case _:
                print(f'Not Implemented: args.user_pref_method = {self.args.user_pref_method}')

    def get_user_budgets(self):
        match self.args.user_budget_method:
            case 'data':
                x = self.data['buyer_budgets']
                return [(b - min(x)) /(max(x) - min(x))*90 + 10 for b in x]
            case 'rand_gen':
                return rand_gen_budgets(self.args)
            case _:
                print(f'Not Implemented: args.user_pref_method = {self.args.user_pref_method}')

    def prep_trait_options_info(self):
        self.trait_options = []
        self.rare_options = []
        for trait, options in self.trait_dict.items():
            self.trait_options.append(list(range(len(options))))
            self.rare_options.append([])
        flat_list = [(item, (i, j)) for i, sublist in enumerate(self.trait_counts) for j, item in enumerate(sublist)]
        k = max(self.args.T, int(self.args.rare_ratio * len(flat_list)))
        min_elements_with_positions = heapq.nsmallest(k, flat_list, key=lambda x: x[0])
        min_positions = [position for element, position in min_elements_with_positions]
        for pos in min_positions:
            trait, attr = pos
            self.rare_options[trait].append(attr)

# methods
def rand_gen_counts(args):
    nft_item_count = [random.randint(1,args.max_nft_count) for __ in range(args.M)]
    return nft_item_count

def rand_gen_preferences(args, trait_dict, allone=False):
    user_preferences = []
    for __ in range(args.N):
        user_pref = []
        for trait, options in trait_dict.items():
            u_pref = []
            for option in options:
                r = 1 if allone else random.random() 
                u_pref.append(r)
            user_pref.append(u_pref)
        user_preferences.append(user_pref)
    return user_preferences

def rand_gen_budgets(args):
    user_budgets = [random.random()*args.max_budget for __ in range(args.N)]
    return user_budgets



if __name__ == '__main__':
    path = 'data/test.json'
    dumpj(nft_example, path)
    print(loadj(path))

