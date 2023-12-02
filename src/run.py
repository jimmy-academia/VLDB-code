from main import main

nft_projects_name = ['Axies', 'BoredApeYachtClub', 'CryptoKitties', 'FatApeClub', 'Heterosis', 'RoaringLeader', 'StepN'] 

def run():
    # child_project
    for project in nft_projects_name:
        main('2+m', project)
def hetero_run():
    for project in nft_projects_name:
        main('3', project)
def homo_run():
    # homogenous
    for project in nft_projects_name:
        main('2+c', project)

if __name__ == '__main__':
    run()
    hetero_run()
    homo_run()
