import hashlib

#d37199212cb457ba30ab03c57a8b7a0a27d66b0f
#9765487b221fba1de9a0e340f7da3d770180b490
a = 231413123122131231
print(hashlib.sha1(a.to_bytes(8, 'big')).hexdigest())