from pathlib import Path
from utils import *
from tqdm import tqdm
from collections import defaultdict
import random

nft_projects_name = ['Axies', 'BoredApeYachtClub', 'CryptoKitties', 'FatApeClub', 'Heterosis', 'RoaringLeader', 'StepN']

min_cap = 1e-5
max_cap = 100

def fetchinfo(transaction, params):
    scale, bias = params
    buyer_add = transaction['buyer_address']
    price = float(transaction['price'])/1e-8
    token_id = int(transaction['token_ids'][0])
    return buyer_add, (price-bias)*scale+min_cap, token_id

def prepare_nft_data():
    trait_dir = Path('data/trait_data')
    buyer_dir = Path('data/buyer_data')
    clean_dir = Path('data/clean')
    clean_dir.mkdir(parents=True, exist_ok=True)
    assert trait_dir.exists() and trait_dir.is_dir()
    assert buyer_dir.exists() and buyer_dir.is_dir()

    for pname in nft_projects_name:
        pfile = clean_dir/f'{pname}.json'
        if pfile.exists(): continue

        trait_output = loadj(trait_dir/'output'/f'{pname}.json') 
        trait_system = loadj(trait_dir/'output'/f'{pname}_traits.json')[0]
        token_id_list = [d["tokenId"] for d in loadj(trait_dir/f'raw_data/{pname}.json')]
        asset_traits = trait_output[0]

        print(f'processing trait for {pname}...')
        match pname:
            case 'Axies' | 'StepN':
                new_token_id_list = []
                new_asset_traits = []
                trigger = 'None' if pname == 'Axies' else 'none'
                for tokenid, attr_list in zip(token_id_list, asset_traits):
                    if trigger not in attr_list:
                        new_token_id_list.append(tokenid)
                        new_asset_traits.append(attr_list)
                token_id_list = new_token_id_list
                asset_traits = new_asset_traits
            case 'BoredApeYachtClub':
                for trait in trait_system.keys():
                    trait_system[trait].append('none')
            case 'RoaringLeader' | 'CryptoKitties':
                for trait in trait_system.keys():
                    trait_system[trait].append('none')
                lastT = -4 if pname == 'RoaringLeader' else -16
                traits = list(trait_system.keys())
                for skip in traits[lastT:]:
                    del trait_system[skip]
                for j in range(len(asset_traits)):
                    asset_traits[j] = asset_traits[j][:lastT] 

        if pname == 'StepN': asset_traits, trait_system = AstepN(asset_traits, trait_system)
        
        print(f'processing trade for {pname}...')
        trade_info = loadj(buyer_dir/f'{pname}/trade.json')['result']

        prices = []
        selected_trade_info = []
        for transaction in trade_info:
            if fetchinfo(transaction, (1, min_cap))[1]>0:
                prices.append(fetchinfo(transaction, (1, 100))[1])
                selected_trade_info.append(transaction)
        # determine params
        bias = min(prices)
        scale = (max_cap - min_cap)/(max(prices) - bias)
        params = (scale, bias)

        match pname:
            case 'StepN':
                asset_traits, item_counts, buyer_budgets, buyer_assets, buyer_assets_ids = connect(asset_traits, token_id_list, selected_trade_info, params)
            case _:
                asset_traits, item_counts, buyer_budgets, buyer_assets, buyer_assets_ids = consolidate(asset_traits, token_id_list, selected_trade_info, params)

        nft_data = {}
        nft_data['trait_system'] = trait_system
        nft_data['asset_traits'] = asset_traits
        nft_data['item_counts'] = item_counts
        nft_data['buyer_budgets'] = buyer_budgets
        nft_data['buyer_assets'] = buyer_assets
        nft_data['buyer_assets_ids'] = buyer_assets_ids

        traits = list(nft_data['trait_system'].keys())
        for asset_traits in tqdm(nft_data['asset_traits'], ncols=88, desc='assert'):
            for t, attribute in enumerate(asset_traits):
                try:
                    assert attribute in nft_data['trait_system'][traits[t]]
                except:
                    input('Oh no!')
                    check()
        assert 0 not in nft_data['item_counts']
        dumpj(nft_data, pfile)
        print(f'processed nft project data for {pname} and saved in {pfile}')

def connect(asset_traits, token_id_list, trade_info, params):
    buyer_set = None
    M = len(asset_traits)

    for __ in range(2):
        buyer_dict = defaultdict(list)
        token_list = []
        for transaction in trade_info:
            if  buyer_set is None or (buyer_add in buyer_set and token_id in token_set):
                buyer_add, price, token_id = fetchinfo(transaction, params)
                buyer_dict[buyer_add].append((token_id, price))
                token_list.append(token_id)

        buyer_set = set([b for b in buyer_dict.keys() if len(buyer_dict[b]) > 1])
        token_set = set(token_list)
        if len(token_set) > M:
            token_set = set(random.sample(list(token_set), M))
        else:
            token_id2tid = {token_id:i for i, token_id in enumerate(token_set)}
            buyer_budgets = []
            buyer_assets = []
            for buyer in buyer_dict.keys():
                buyer_budgets.append(sum([t[1] for t in buyer_dict[buyer]]))
                buyer_assets.append([asset_traits[token_id2tid[t[0]]] for t in buyer_dict[buyer]])
            # print('StepN connect is success')
            break
    # combine and get item_count
    asset_set = set(tuple(asset) for asset_list in buyer_assets for asset in asset_list)

    item_counts = [0]* len(asset_set)
    atuple2id = {atuple:i for i, atuple in enumerate(asset_set)}
    for asset in asset_traits:
        if tuple(asset) in asset_set:
            item_counts[atuple2id[tuple(asset)]] += 1
    buyer_assets_ids = []
    for asset_list in buyer_assets:
        buyer_list = []
        for asset in asset_list:
            buyer_list.append(atuple2id[tuple(asset)])
        buyer_assets_ids.append(buyer_list)
    asset_traits = list(asset_set)
    for j, count in enumerate(item_counts):
        if count > 5:
            item_counts[j] = random.randint(1,5)
            asset_traits.append(asset_traits[j])
            item_counts.append(random.randint(1,3))

    return asset_traits, item_counts, buyer_budgets, buyer_assets, buyer_assets_ids

def consolidate(asset_traits, token_id_list, trade_info, params):
    buyer_add2bid = {}
    buyer_budgets = []
    buyer_assets = []
    buyer_assets_ids = []
    atuple2aid = {}
    item_counts = []
    new_asset_traits = []
    # organized_trade = []
    for transaction in tqdm(trade_info, ncols=88, desc='conso-iter-trade'):
        buyer_add, price, token_id = fetchinfo(transaction, params)
        if token_id in token_id_list:
            asset = asset_traits[token_id_list.index(token_id)]
            atuple = tuple(asset)
            if atuple not in atuple2aid:
                atuple2aid[atuple] = len(atuple2aid)
                new_asset_traits.append(asset)
                item_counts.append(1)
            else:
                item_counts[atuple2aid[atuple]] += 1
            aid = atuple2aid[atuple]
            if buyer_add in buyer_add2bid:
                bid = buyer_add2bid[buyer_add]
                buyer_budgets[bid] += price
                buyer_assets[bid].append(asset)
                buyer_assets_ids[bid].append(aid)
            else:
                buyer_add2bid[buyer_add] = bid = len(buyer_add2bid)
                buyer_budgets.append(price)
                buyer_assets.append([asset])
                buyer_assets_ids.append([aid])
            # organized_trade.append((bid, aid, price))
    return new_asset_traits, item_counts, buyer_budgets, buyer_assets, buyer_assets_ids

def reduce_load():
    clean_dir = Path('data/clean')
    small_dir = Path('data/small')
    small_dir.mkdir(parents=True, exist_ok=True)
    setting = {'Axies':(4, 0.9), 'BoredApeYachtClub':(4, 0), 'CryptoKitties':(3, 0), 'FatApeClub': (2, 0), 'RoaringLeader':(4, 0)}
    rerun = False
    print()
    for pname in nft_projects_name:
        minp, pp = setting[pname] if pname in setting else (0,0)
        if not (clean_dir/f'{pname}.json').exists(): continue
        pfile = small_dir/f'{pname}.json'
        # if pfile.exists() and not rerun: rerun = ask_proceed()
        if pfile.exists(): continue

        nft_data = loadj(clean_dir/f'{pname}.json')

        buyer_list = []
        all_assets = []
        for i, asset_list in enumerate(nft_data['buyer_assets']):
            if len(asset_list) > minp and random.random()>pp:
                buyer_list.append(i)
                for x in asset_list:
                    all_assets.append(tuple(x))

        all_assets = set(all_assets)
        new_asset_traits = []
        new_item_counts = []
        for asset_list, item_count in zip(nft_data['asset_traits'], nft_data['item_counts']):
            if tuple(asset_list) in all_assets:
                new_asset_traits.append(asset_list)
                if pname == 'Axies' and item_count > 5: item_count = random.randint(1,4)
                new_item_counts.append(item_count)
        old_asset_traits = nft_data['asset_traits']
        nft_data['asset_traits'] = new_asset_traits
        nft_data['item_counts'] = new_item_counts
        nft_data['buyer_budgets'] = [nft_data['buyer_budgets'][i] for i in buyer_list]
        nft_data['buyer_assets'] = [nft_data['buyer_assets'][i] for i in buyer_list]

        asset_set = set([tuple(asset) for asset in nft_data['asset_traits']])
        atuple2id = {atuple:i for i, atuple in enumerate(asset_set)}
        buyer_assets_ids = []
        for asset_list in nft_data['buyer_assets']:
            buyer_assets = []
            for asset in asset_list:
                buyer_assets.append(atuple2id[tuple(asset)])
            buyer_assets_ids.append(buyer_assets)

        nft_data['buyer_assets_ids'] = buyer_assets_ids
        print(pname, list(map(lambda x: len(nft_data[x]), ['asset_traits', 'item_counts', 'buyer_budgets', 'buyer_assets', 'buyer_assets_ids'])))
        dumpj(nft_data, pfile)

def AstepN(asset_traits, trait_system):
    names = ['Efficiency', 'Comfort', 'Durability', 'Luck', 'Efficiency-lv1', 'Comfort-lv1', 'Durability-lv1', 'Luck-lv1', 'Efficiency-lv2', 'Comfort-lv2', 'Durability-lv2', 'Luck-lv2', 'Gem',]
    socket1 = [22036, 21577, 20264, 18207, 1546, 944, 828, 681, 603, 575, 352, 242, 220]
    socket2 = [23864, 22188, 21187, 19316, 396, 380, 356, 206, 179, 163, 144, 136, 103]
    trait_system['socket1'] = names
    trait_system['socket2'] = names
    M = len(asset_traits)
    attr1_list = random.choices(range(len(socket1)), weights=socket1, k=M)
    attr2_list = random.choices(range(len(socket2)), weights=socket2, k=M)
    new_asset_traits = []
    for asset, attr1, attr2 in zip(asset_traits, attr1_list, attr2_list):
        new_asset_traits.append(asset+[names[attr1], names[attr2]])
    
    return new_asset_traits, trait_system


if __name__ == '__main__':
    prepare_nft_data()
    reduce_load()
    # zip -r -X trait_data.zip trait_data -x "__MACOSX*" "*.DS_Store"
    