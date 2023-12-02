import math
from statistics import pstdev
import torch
import random
from tqdm import tqdm
from utils import *


import configparser
from itertools import combinations, product


class BaseSolver:
    def __init__(self, args, nft_project, buyer_types=None):
        self.args = args
        self.nftP = nft_project
        self.buyer_types = buyer_types

        cache_file = self.args.cache_dir/'cache_AttAirVj.pth'
        if cache_file.exists():
            self.alpha, self.Att, self.Air, self.Vj = torch.load(cache_file, map_location=args.device)
        else:
            self.prepare_AttAirVj()
            torch.save((self.alpha, self.Att, self.Air, self.Vj), cache_file)

        self.Uij = torch.matmul(self.Air, self.Att.T)

        info = self.args.breeding_util.split('+')
        self.b_args = configparser.ConfigParser()
        self.b_args.pnum = int(info[0])                         # number of parent NFTs
        self.b_args.gtype = info[1] if len(info)>1 else 'n'     # type of genetic muation

        if not (self.b_args.pnum ==2 and self.b_args.gtype == 'n') :
            cache_top_pair = self.args.ckpt_dir/f'cache_toppair.pth'  ## use ckpt: different by breeding!
            if cache_top_pair.exists():
                self.top_pairs, self.top_expectations = torch.load(cache_top_pair, map_location=args.device)
            else:
                self.prepare_top_pairs()
                torch.save([self.top_pairs, self.top_expectations], cache_top_pair)
            self.top_pairs = self.top_pairs.to(self.args.device)
            self.top_expectations = self.top_expectations.to(self.args.device)
            self.parent_trait_count = None

    def random_propotional_prices(self, israndom=True):
        total_spending = 0
        mean = sum(self.nftP.user_budgets)/sum(self.nftP.item_count)
        if israndom:
            prices = torch.rand(self.args.M) * mean 
            prices = prices.to(self.args.device)
        else:  
            # popular
            spendings = self.Uij + self.Vj
            spendings = torch.zeros_like(spendings)
            spendings.scatter_(1, spendings.topk(self.args.M//5)[1], True)
            spendings /= spendings.sum(1, keepdims=True) 
            spendings = torch.Tensor(self.nftP.user_budgets).to(self.args.device).unsqueeze(1)* spendings 
            prices = spendings.sum(0)/torch.LongTensor(self.nftP.item_count).to(self.args.device)
            prices = torch.where(prices > 0, prices, 1e-1)
        return prices
    
    def solve(self):        
        self.final_prices = self.random_propotional_prices(self.args.method == 'random')

    def prepare_AttAirVj(self):
        nsel_list = [len(options) for (__, options) in self.nftP.trait_dict.items()]
        flatonehot = []
        for item_vec in self.nftP.item_vec_list:
            itemonehot = []
            for x, nsel in zip(item_vec, nsel_list):
                onehot = torch.zeros(nsel)
                onehot[x] = 1
                itemonehot.append(onehot)
            flatonehot.append(torch.cat(itemonehot))
        self.Att = torch.stack(flatonehot).to(self.args.device)

        flatpreferences = []
        for user_pref in self.nftP.user_preferences:
            flatpreferences.append(torch.Tensor([it for sub in user_pref for it in sub])) 
        self.Air = torch.stack(flatpreferences).to(self.args.device) + 1

        raw_value = []
        for item_vec in self.nftP.item_vec_list:
            u = 0
            for attr_id, count in zip(item_vec, self.nftP.trait_counts):
                u += torch.log(torch.Tensor([self.args.M / max(1, count[attr_id])]))
            raw_value.append(u)
        raw_value = torch.cat(raw_value).to(self.args.device)
        
        total_raw_value = total_budget = 0
        for i in range(self.args.N):
            total_raw_value += sum([raw_value[aid] for aid in self.nftP.data['buyer_assets_ids'][i] if aid < len(self.nftP.item_vec_list)])
            total_budget += self.nftP.user_budgets[i]

        self.alpha = total_budget/total_raw_value 
        self.Vj = raw_value * self.alpha

    def prepare_top_pairs(self):
        self.top_pairs = []
        self.top_expectations = []
        self.attr_alpha = []

        if self.b_args.pnum != 2:
            ## prepare div, class for heterogeneous
            n_attr_cls = 3
            cache_list_div_class = self.args.cache_dir/f'cache_listdiv.pth'
            if cache_list_div_class.exists():
                self.list_div_class = torch.load(cache_list_div_class)
            else:
                self.list_div_class = []
                for j in range(self.args.M):
                    t = random.choice(range(n_attr_cls))
                    rc = self.nftP.item_vec_list[j][t] % n_attr_cls
                    self.list_div_class.append((t, rc))
                torch.save(self.list_div_class, cache_list_div_class)

            atr_list = torch.LongTensor([ind % n_attr_cls for options in self.nftP.trait_counts for ind in range(len(options))])
            self.Airc = torch.stack([torch.mean(self.Air[:, atr_list == k], 1) for k in range(n_attr_cls)]).T
        
        for i in tqdm(range(self.args.N), desc=f'iterate buyer for top pairs', ncols=88):
            if self.b_args.pnum == 2:
                # Homogeneous and child-project
                candidate = (self.Uij[i]+self.Vj).topk(self.args.ctopk)[1]
                p_combinations = torch.LongTensor(list(combinations(candidate.tolist(), self.b_args.pnum)))
                exp_breedings = self.breeding_expectation(i, p_combinations)
                self.top_pairs.append(p_combinations)
                self.top_expectations.append(exp_breedings)
            else:
                # Heterogeneous
                candidate = (self.Uij[i]+self.Vj).topk(self.args.M)[1]
                if self.buyer_types is None:
                    buyer_type = random.randint(0, 1) #niche or eclectic collector
                else:
                    buyer_type = self.buyer_types[i]
                p_combinations = []
                p_comb_rc = []
                for ind, j in enumerate(candidate):
                    pcomb = [j]
                    t,rc = self.list_div_class[j]
                    tset = [t]
                    rc_list = [rc]
                    for q in candidate[ind+1:]:
                        qt, qrc = self.list_div_class[q]
                        condition = qrc == rc if buyer_type else qrc not in rc_list
                        if qt not in tset and condition:
                            pcomb.append(q)
                            tset.append(qt)
                            rc_list.append(qrc)
                        if len(tset) == n_attr_cls: break
                    if len(tset) == n_attr_cls: 
                        p_combinations.append(torch.stack(pcomb))
                        p_comb_rc.append(rc_list)
                    if len(p_combinations) == self.args.ctopk * (self.args.ctopk+1)//2: break

                target_length = self.args.ctopk * (self.args.ctopk+1)//2
                current_length = len(p_combinations)

                if current_length != target_length: 
                    p_combinations = p_combinations* (target_length//current_length + 1)
                    p_comb_rc = p_comb_rc* (target_length//current_length + 1)
                    p_combinations = p_combinations[:target_length]
                    p_comb_rc = p_comb_rc[:target_length]

                p_combinations = torch.stack(p_combinations)
                p_comb_rc = torch.LongTensor(p_comb_rc)
                exp_breedings = (self.Vj[p_combinations] * self.Airc[i][p_comb_rc]).sum(1)*n_attr_cls
                self.top_pairs.append(p_combinations)
                self.top_expectations.append(exp_breedings.tolist())

        self.top_pairs = torch.stack(self.top_pairs)
        self.top_expectations = torch.Tensor(self.top_expectations)

    def breeding_expectation(self, i, parents):
        item_vec_list = torch.LongTensor([self.nftP.item_vec_list[a] for a in parents.flatten()]).view(parents.size(0), parents.size(1), -1)

        mutation_rate = self.args.mutation_rate
        expectation = 0

        rare_thresh = 1/torch.LongTensor([len(x) for x in self.nftP.rare_options]) + 1e-5
        normal_thresh = 1/torch.LongTensor([len(x) for x in self.nftP.trait_options]) + 1e-5
        trait_count = torch.LongTensor(padd_list(self.nftP.trait_counts))
    
        item_vec_list, rare_thresh, normal_thresh, trait_count = map(lambda x: x.to(self.args.device), [item_vec_list, rare_thresh, normal_thresh, trait_count])

        for _ in range(self.args.mutation_samples):
            combination = torch.randint(self.b_args.pnum, (self.args.T,))
            combination = torch.eye(self.args.T)[combination].T[:self.b_args.pnum]
            combination = combination.long().to(self.args.device)

            child_item_vec = (item_vec_list*combination).sum(1).long()

            if self.b_args.gtype != 'n':
                m_mask = (torch.rand(self.args.T) <= mutation_rate).to(torch.float32).to(self.args.device)
                if m_mask.sum() > 0:
                    m_mask.expand_as(child_item_vec)
                    thresh = rare_thresh if self.b_args.gtype == 'm' else normal_thresh
                    random_child = (torch.rand(self.args.T).to(self.args.device) / thresh).long()
                    child_item_vec = child_item_vec *  (1-m_mask) + random_child * m_mask
                    child_item_vec = child_item_vec.long()


            rarity = torch.take_along_dim(trait_count.T, child_item_vec, dim=0)
            u = torch.sum((self.args.M / rarity), dim=1)

            if self.b_args.gtype == 'f':
                cost = torch.sum(self.Vj[parents], dim=1)
                u *= self.b_args.pnum
                expectation -= cost
            expectation += u
        expectation /= (self.args.mutation_samples)
        return expectation.tolist()

    def hatrelu(self, x, threshold=1):
        return threshold - torch.nn.functional.relu(threshold-x)


    def calculate_utility(self, holding, prices, spending_var, batch_budget, user_index):
        '''
        U^i = U^i_{Item} + U^i_{Collection} + U^i{Breeding}
        U^i_{Item} = sum_j v_j * multistep(x^i[j], Q[j])
        U^i_{Collection} = sum_r  a^i_r log (sum_j multistep(x^i[j], Q[j]) t_jr)
        U^i_{Breeding} = sum_k topk expectation value * multistep(x^i[p], Q[p]) * multistep(x^i[q], Q[q])
        '''
        U_item = (holding * (self.Vj)).sum(1)
        # Batchwise operation
        result_list = []
        chunk_size = 32 # Adjust as needed
        for i in range(0, len(user_index), chunk_size):
            holding_chunk = holding[i:i + chunk_size]
            result_chunk = (holding_chunk.unsqueeze(2) * self.Att).sum(1)
            result_list.append(result_chunk)
        result = torch.cat(result_list, dim=0)
        U_coll = (torch.log(result+1) * self.Air[user_index]).sum(1)

        if self.b_args.gtype != 'n':
            # breeding
            bbtop_pair = self.top_pairs[user_index]
            bbtop_expectations = self.top_expectations[user_index]

            breedweight = holding.clone()
            cost = torch.take(prices, bbtop_pair).sum(2)
            U_breed = torch.zeros_like(U_item)
            breed_sum = torch.zeros_like(U_item)
            probability = torch.take(breedweight, bbtop_pair).prod(2)
            jlists = torch.argsort((bbtop_expectations/cost)* (probability > 0), 1, descending=True)

            for jlist in jlists.T:
                dummy_indices = torch.arange(len(jlist))
                the_prob = probability[dummy_indices, jlist]
                the_exp = bbtop_expectations[dummy_indices, jlist]
                breed_sum += the_prob

                factor = 1 
                if self.b_args.gtype == 'c':
                    the_parents = bbtop_pair[torch.arange(bbtop_pair.shape[0]), jlist]
                    parent_count[the_parents[:, 0]] += the_prob.data
                    parent_count[the_parents[:, 1]] += the_prob.data
                    if self.parent_trait_count is not None:
                        factor = (self.Att[the_parents[:, 0]] * self.parent_trait_count).sum(1) + (self.Att[the_parents[:, 1]] * self.parent_trait_count).sum(1) 
                        factor = 1/(factor+1e-5)
                        factor = torch.log(1+factor)
                        factor = factor*2/ factor.sum()

                U_breed += the_exp * the_prob * (breed_sum < self.args.breeding_topk) * factor
                if any(torch.isnan(U_breed)):
                    check() 
            utility = (U_item + U_coll + self.args.gamma* U_breed) + batch_budget * spending_var[:, -1]
        else:
            utility = (U_item + U_coll) + batch_budget * spending_var[:, -1]
        return utility

    def solve_user_demand(self, prices):
        self.budget = torch.Tensor(self.nftP.user_budgets).to(self.args.device)
        spending = torch.rand(self.args.N, self.args.M+1).to(self.args.device)
        spending /= spending.sum(1).unsqueeze(1)

        num_samples = self.args.N // 10
        batch_user_index_list = []
        remain = self.args.N
        weight = self.budget.clone()
        while remain > 0:
            if remain < num_samples*2: remain = num_samples
            user_index = torch.multinomial(self.budget, num_samples, replacement=False)
            batch_user_index_list.append(user_index)
            weight[user_index] = 0
            remain -= num_samples

        pbar = tqdm(range(self.args.user_iters), ncols=88, desc='Solving user demand!', leave=False)
        r_budget = spending[:, -1].sum()

        for it in pbar:
            parent_count = torch.zeros_like(prices)
            for user_index in batch_user_index_list:
                spending_var = spending[user_index]
                spending_var.requires_grad = True
                batch_budget = self.budget[user_index]

                holding = self.hatrelu(spending_var[:, :-1]*batch_budget.unsqueeze(1)/prices.unsqueeze(0))
                utility = self.calculate_utility(holding, prices, spending_var, batch_budget, user_index)
                utility.backward(torch.ones_like(utility))
                spending[user_index] += self.args.user_eps* spending_var.grad
                spending = torch.where(spending < 0, 0, spending)
                spending /= spending.sum(1).unsqueeze(1)

            if self.b_args.gtype == 'c':
                self.parent_trait_count = (self.Att * parent_count.unsqueeze(1)).sum(0)
            delta = r_budget - spending[:, -1].sum()
            pbar.set_postfix(delta= float(delta))

            r_budget = spending[:, -1].sum()

        demand = self.hatrelu(spending[:, :-1]*self.budget.unsqueeze(1)/prices.unsqueeze(0))
        self.budget = (demand* prices).sum(1)
        return demand


    