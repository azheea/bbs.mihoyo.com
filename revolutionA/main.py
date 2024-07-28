import re
from collections import OrderedDict

with open("web.txt", "r", encoding="utf-8") as f:
    text = f.read()

pattern_level = r'level(\w+)\.png'
matches_level = re.findall(pattern_level, text)


count_dict_level = {}
for match in matches_level:
    x = match
    if x in count_dict_level:
        count_dict_level[x] += 1
    else:
        count_dict_level[x] = 1

# 按照等级从小到大排序
count_dict_level_sorted = OrderedDict(sorted(count_dict_level.items(), key=lambda t: int(t[0])))

print("等级:")
for x, count in count_dict_level_sorted.items():
    print(f"{x}: {count}")


pattern_from = r'来自(\w+)'
matches_from = re.findall(pattern_from, text)

count_dict_from = {}
for match in matches_from:
    xx = match
    if xx in count_dict_from:
        count_dict_from[xx] += 1
    else:
        count_dict_from[xx] = 1

print("地区：")
for xx, count in count_dict_from.items():
    print(f"{xx}: {count}")

print(f"收集到的等级数据共{len(matches_level)}\n收集到的地区数据共{len(matches_from)}")