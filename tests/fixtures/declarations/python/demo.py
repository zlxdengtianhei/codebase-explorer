LIMIT = 8
mutable = 1
computed = object()
x = y = 2
class Box:
    FIELD = 4
    def get(self): return LIMIT
def helper(x): return x + LIMIT
