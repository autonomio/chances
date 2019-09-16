def random_org(n, start, end):

    '''
    Implements the random.org ambience random number generator.
    '''

    key = 'c7d1e0b0-e57c-4fb8-9d5b-382ec9de5a89'

    import requests
    import json

    url = 'https://api.random.org/json-rpc/2/invoke'

    data = {"jsonrpc": "2.0",
            "method": "generateIntegerSequences",
            "params":
                    {"apiKey":key,
                     "n":1,
                     "length": n,
                     "min": start,
                     "max": end,
                     "replacement": True,
                     "base":10},
            "id":1418}

    params = json.dumps(data)

    response = requests.post(url, data=params, headers={'content-type': 'application/json'})

    return json.loads(response.text)['result']['random']['data'][0]
