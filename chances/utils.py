def generate_random_alpha(n=1, dtype=str):

    '''Generates a random sequence of alphabets.
    n : int
        Length of the sequence
    dtype : list or str
        Output is either string or list.

    '''

    import string
    import numpy as np

    out = ''
    alpha = string.ascii_lowercase

    for i in range(n):
        out += alpha[np.random.randint(len(alpha))]

    if dtype == list:
        return [i for i in out]
    elif dtype == str:
        return out
