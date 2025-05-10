# The output is a file is a **json** (gnb_ues.json) of format: {gNB<i>: number of UEs}.
# The overall mean of UE count per gNB is guaranteed to be equal to 2
# Note: the number of UEs must be an even number from 6-50
#       I just supposed that the MAX UE = 50
import random
import json

def random_array_with_sum(N, K):
    '''
     returns an array of length K, that has sum = N (array[i] is the number of UPFs in gNB i)
    '''
    t = N
    if K > N:
        raise ValueError("N must be at least K, since each element must be ≥ 1")
    print(f'Distributing {N} UPFs in {K} gNB')
    spots = []
    for spot in range(K):
     possible = random.randint(1, N - (K - spot - 1))

     spots.append(possible)
     N = N - possible
    for i in range(K // 2):
     max_index = spots.index(max(spots))
     min_index = spots.index(min(spots))
    
     spots[max_index] = spots[max_index] - 1
     spots[min_index] = spots[min_index] + 1
    return spots

if __name__ == '__main__':
        ue_count = int(input('UE count (6 to 50)= '))
        while ue_count % 2 == 1 or not( 6 <= ue_count <= 50):
         ue_count = int(input('Please enter an even UE count that is in range [6, 50]:\n'))
        gnb_count = ue_count // 2
        ue_distribution = random_array_with_sum(ue_count, gnb_count)
        gnb_ues = {f"gNB{i+1}": ue_distribution[i] for i in range(gnb_count)}

        print('UE distribution: ', ue_distribution)
        with open('gnb_ues.json', 'w') as f:
                json.dump(gnb_ues, f, indent=2)
        print('Saved to gnb_ues.json')
