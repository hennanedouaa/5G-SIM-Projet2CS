def configure_upf_placement(string1, string2):
    """
    Prints the two input strings and returns 0 if successful, 1 otherwise.

    Args:
        string1 (str): The first string.
        string2 (str): The second string.

    Returns:
        int: 0 if successful, 1 otherwise.
    """
    try:
        print(f"String 1: {string1}")
        print(f"String 2: {string2}")
        return 0
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1