import requests
import json
import jieba
from wordcloud import WordCloud
import matplotlib.pyplot as plt

lastid = 0
replys = []
ip_region_counts = {}
nickname_counts = {}
level_counts = {}
content_counts = {}
passageid = 55221094

# 定义停用词列表
stopwords = ["我", "了", "的", "你", "不", "啊", "吧", "呀","有","吗","_","-","米游姬","开拓者","拉尼","阿姬","米游兔","流萤","萨姆","心情简单","三月七" ,"也", "都","bbs","mihoyo","就","是","img","src","https","upload","miyoshe"]

while True:
    returnt = requests.get(url=f"https://bbs-api.miyoushe.com/post/wapi/getPostReplies?gids=5&is_hot=true&last_id={lastid}&post_id={passageid}&size=50")
    returnt_data = json.loads(returnt.text).get("data").get("list")
    
    print(lastid)
    lastid += 50
    
    if len(returnt_data) == 0:
        print(lastid)
        break
    
    for item in returnt_data:
        reply = item.get("reply")
        content = reply.get("content")
        ip_region = item.get("user").get("ip_region")
        nickname = item.get("user").get("nickname")
        level = item.get("user").get("level_exp").get("level")
        
        # 将回复内容添加到列表中
        replys.append(content)
        
        # 统计ip_region出现的次数
        ip_region_counts[ip_region] = ip_region_counts.get(ip_region, 0) + 1
        
        # 统计nickname出现的次数
        nickname_counts[nickname] = nickname_counts.get(nickname, 0) + 1
        
        # 统计level出现的次数
        level_counts[level] = level_counts.get(level, 0) + 1
        
        # 统计content出现的次数
        content_counts[content] = content_counts.get(content, 0) + 1

# 将重复次数大于1的统计结果写入到JSON文件
output_data = {
    "ip_region_counts": {ip_region: count for ip_region, count in ip_region_counts.items() if count > 1},
    "nickname_counts": {nickname: count for nickname, count in nickname_counts.items() if count > 1},
    "level_counts": {level: count for level, count in level_counts.items() if count > 1},
    "content_counts": {content: count for content, count in content_counts.items() if count > 1}
}

# 写入JSON文件
with open("./revolutionB/statistics.json", "w", encoding="utf-8") as json_file:
    json.dump(output_data, json_file, ensure_ascii=False, indent=4)

# 打印回复总数
print(len(replys))

# 将所有回复写入文件
with open("./revolutionB/all_replys.json", "w", encoding="utf-8") as json_file:
    json.dump(replys, json_file, ensure_ascii=False, indent=4)

# 将所有回复内容合并成一个字符串
text = ' '.join(replys)

# 使用jieba进行分词
wordlist = jieba.cut(text, cut_all=False)
filtered_words = [word for word in wordlist if word not in stopwords]

# 将分词结果转换成空格分隔的字符串
words = ' '.join(filtered_words)

# 设置词云参数
wordcloud = WordCloud(width=800, height=400, background_color='white', font_path=r'C:\Windows\Fonts\simfang.ttf', 
                      max_words=200, colormap='rainbow', contour_width=1, contour_color='black')

wordcloud.generate(words)
# 绘制词云
plt.figure(figsize=(10, 6))
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis('off')
plt.show()