# Generate K > 3 available spots in order to put 3 UPF 
# (the spots are in a 10x10km surface).
# converted to longitude, latitude
# OUTPUT: upf_placement.json that has three entries: {i: (lon, lat) for i in {1, 2, 3}}
import random
import json
import math

def meters_to_latlon(coord: tuple[int, int], origin_lat: float, origin_lon: float):
    """
    Convert (x, y) in meters to (lat, lon) using a flat-earth approximation.
    coord: Tuple (x, y) in meters
    origin_lat, origin_lon: Reference latitude and longitude in degrees
    Returns: Tuple (lat, lon) rounded to 6 decimal places
    """
    x, y = coord
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 111320 * math.cos(math.radians(origin_lat))

    delta_lat = y / meters_per_deg_lat
    delta_lon = x / meters_per_deg_lon

    lat = origin_lat + delta_lat
    lon = origin_lon + delta_lon

    return round(lat, 6), round(lon, 6)

def random_spots(K:int = 10):
	return [(random.randint(0, 10000), random.randint(0, 10000)) for i in range(K)]

if __name__ == '__main__':
    available_spots = random_spots()
    upf_spot = {}

    auto = input('Would you like automatic UPF placement? y/n: ').strip().lower()

    if auto == 'y':
        for i in range(3):
            chosen_index = random.randint(0, len(available_spots) - 1)
            chosen_spot = available_spots[chosen_index]
            upf_spot[i + 1] = meters_to_latlon(chosen_spot, 36.7529, 3.0420)
            print(f"Automatically assigned spot for UPF {i+1}: {upf_spot[i+1]}")
            del available_spots[chosen_index]
    else:
        for i in range(3):
            print('\nAvailable spots:')
            for j, spot_name in enumerate(available_spots):
                print(f'{j + 1}) {spot_name}')
            try:
                spot = int(input(f'Pick spot for UPF {i+1}: '))
                while spot <= 0 or spot > len(available_spots):
                    print('Unavailable')
                    spot = int(input(f'Pick spot for UPF {i+1}: '))
                selected_spot = available_spots[spot - 1]
                upf_spot[i + 1] = meters_to_latlon(selected_spot, 36.7529, 3.0420)
                print(f'Spot for UPF {i+1} is {upf_spot[i+1]}')
                del available_spots[spot - 1]
            except ValueError:
                print("Invalid input. Please enter a number.")
                continue

    print("\nFinal UPF placements:")
    for k, v in upf_spot.items():
        print(f'UPF {k}: {v}')

    with open('upf_coords.json', 'w') as f:
        json.dump(upf_spot, f, indent=2)
    print("\nUPF coordinates saved to upf_coords.json .")
