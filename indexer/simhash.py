import hashlib

def shingles(tokens, k=5):
    return [' '.join(tokens[i:i+k]) for i in range(len(tokens)-k+1)]


def hash64(x):
    return int(hashlib.md5(x.encode()).hexdigest(), 16) & ((1<<64)-1)

def simhash(shingles):
    v = [0] * 64
    for sh in shingles:
        h = hash64(sh)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    # build final fingerprint
    fp = 0
    for i in range(64):
        if v[i] > 0:
            fp |= (1 << i)
    return fp

def hamming(a, b):
    return bin(a ^ b).count("1")
