import numpy as np

try:
    matplotlib
except NameError:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt


def oned(data):

    '''1-d visualization for 1-d random sequences

    EXAMPLE
    =======

    test = random.sample(list(range(65000)),300)
    randhist(test)

    '''

    plt.figure(figsize=(12, 1))
    plt.eventplot(data,
                  orientation='horizontal',
                  colors='black',
                  linewidths=.8)
    plt.axis('off')
    plt.show()


def twod(x, y=None, plot_title=''):

    '''2-d visualization for 1-d or 2-d random sequences.
    In the case of input being 1-d sequence, it will be split
    in half to fit into 2-d plane.
    '''

    if y is None:

        # split two columns in x into x and y
        if len(np.array(x).shape) == 2:
            y = x[:, 1]
            x = x[:, 0]

        # split 1d x into two columns
        else:
            x_len = int(len(x) / 2)
            y = x[x_len:]
            x = x[:x_len]

    plt.scatter(x=x, y=y, color='black', s=8, alpha=.4)
    plt.title(plot_title)
