from utils.distance import configure_upf_placement
from utils.traffic import generate_urllc_traffic


def main():
    try:
        coords_input = input("Enter UPF coordinates (format: x,y): ")
        x_str, y_str = coords_input.strip().split(',')
        coordinates = (float(x_str), float(y_str))

        if configure_upf_placement(coordinates) and generate_urllc_traffic():
            print("Performance metrics are in performance.txt")
        else:
            print("One or more operations failed.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
