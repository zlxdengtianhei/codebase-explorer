"""E2b（D-63）25 步部分的 24 题：E1 十道试点题加分层补抽 14 题；另定补抽减到 6 题时取哪 6 题。看 E2a 数据前跑。"""
import json, random, sys
L = json.load(open(sys.argv[1]))["labels"]
pilot = [4, 6, 11, 12, 14, 20, 32, 41, 46, 47]
cell = {}
for x in L:
    cell.setdefault((x["swe_type"], x["layer"]), []).append(x["qid"])
# 每类 6 题（24/4），类内按层的比例取最大余数；余数相同时给样本里还没有的层（E1 的做法：唯一的第 1 层题 41 必入）
target = {("What", 2): 2, ("What", 3): 2, ("What", 4): 2,
          ("How", 2): 3, ("How", 3): 2, ("How", 4): 1,
          ("Why", 4): 5, ("Why", 2): 1,
          ("Where", 3): 4, ("Where", 2): 1, ("Where", 1): 1}
rng = random.Random(20261017)
extra = {}
for k in sorted(target, key=lambda k: (["What", "How", "Why", "Where"].index(k[0]), k[1])):
    have = [q for q in pilot if q in cell[k]]
    need = target[k] - len(have)
    pool = sorted(q for q in cell[k] if q not in pilot)
    assert need >= 0 and need <= len(pool), (k, need, pool)
    extra.setdefault(k[0], []).extend(sorted(rng.sample(pool, need)))
order = {t: rng.sample(v, len(v)) for t, v in extra.items()}
six = sorted(order["What"][:1] + order["How"][:1] + order["Why"][:2] + order["Where"][:2])
q14 = sorted(q for v in extra.values() for q in v)
out = {"seed": 20261017, "qid_base": 0, "pilot10": pilot, "extra14": q14, "extra6_if_reduced": six,
       "q24": sorted(pilot + q14), "q16_if_reduced": sorted(pilot + six),
       "design": "每类 What/How/Why/Where 6 题；类内按层比例取最大余数，余数相同给样本里还没有的层；格内用种子随机抽。减到 6 题时每类按同一种子打乱后取前 1、1、2、2 题（What、How、Why、Where）。",
       "per_type_extra": extra}
print(json.dumps(out, ensure_ascii=False, indent=1))
