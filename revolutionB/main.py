import requests
import json
import threading
import time
from datetime import datetime
from collections import OrderedDict

# 全局变量
lastid = 0
all_reply = {}
ip_region_counts = {}
nickname_counts = {}
level_counts = {}
content_counts = {}

passageid = 55221094

# 创建锁
lock = threading.Lock()

def fetch_data(thread_id):
    global lastid, all_reply, ip_region_counts, nickname_counts, level_counts, content_counts
    
    while True:
        with lock:
            current_lastid = lastid
            lastid += 50
        
        try:
            returnt = requests.get(url=f"https://bbs-api.miyoushe.com/post/wapi/getPostReplies?gids=2&is_hot=true&last_id={current_lastid}&post_id={passageid}&size=50")
            returnt.raise_for_status()  # 检查是否有网络请求错误

            returnt_data = returnt.json().get("data", {}).get("list", [])

            if not returnt_data:
                break
            
            print(f"Thread {thread_id}: Fetching data from {current_lastid} to {current_lastid + 50}")

            for item in returnt_data:
                reply = item.get("reply")
                uid = reply.get("uid")
                content = reply.get("content")
                ip_region = item.get("user", {}).get("ip_region")
                reply_id = reply.get("reply_id")
                nickname = item.get("user", {}).get("nickname")
                level = item.get("user", {}).get("level_exp", {}).get("level")
                created_at = reply.get("created_at")
                floor_id = reply.get("floor_id")
                
                slave_reply = get_slave_reply(floor_id, current_lastid)
                
                # 加锁
                with lock:
                    all_reply[reply_id] = {
                        "nickname": nickname,
                        "level": level,
                        "content": content,
                        "ip_region": ip_region,
                        "uid": uid,
                        "created_at": created_at,
                        "floor_id": floor_id,
                        "slave_reply": slave_reply
                    }
                    # 统计ip_region出现的次数
                    ip_region_counts[ip_region] = ip_region_counts.get(ip_region, 0) + 1

                    # 统计nickname出现的次数
                    nickname_counts[nickname] = nickname_counts.get(nickname, 0) + 1

                    # 统计level出现的次数
                    level_counts[level] = level_counts.get(level, 0) + 1

                    # 统计content出现的次数
                    content_counts[content] = content_counts.get(content, 0) + 1

        except requests.exceptions.RequestException as e:
            # print(f"Thread {thread_id}: Exception occurred: {str(e)}")
            print(f"Thread {thread_id}: Waiting for 1 second before retrying...")
            time.sleep(20)  # 等待10秒钟后重试
            continue  # 继续下一次循环尝试重新请求

def get_slave_reply(floor_id, current_lastid):
    try:
        time.sleep(0.5)
        returnt = requests.get(url=f"https://bbs-api.miyoushe.com/post/wapi/getSubReplies?floor_id={floor_id}&gids=2&is_hot=true&last_id={current_lastid}&post_id={passageid}&size=50")
        returnt.raise_for_status()  # 检查是否有网络请求错误

        returnt_data = returnt.json().get("data", {}).get("list", [])

        if not returnt_data:
            return {}

        slave_reply = {}
        for item in returnt_data:
            reply = item.get("reply")
            uid = reply.get("uid")
            content = reply.get("content")
            ip_region = item.get("user", {}).get("ip_region")
            reply_id = reply.get("reply_id")
            nickname = item.get("user", {}).get("nickname")
            level = item.get("user", {}).get("level_exp", {}).get("level")
            created_at = reply.get("created_at")
            floor_id = reply.get("floor_id")
            
            slave_reply[reply_id] = {
                "nickname": nickname,
                "level": level,
                "content": content,
                "ip_region": ip_region,
                "uid": uid,
                "created_at": created_at,
                "floor_id": floor_id
            }

        return slave_reply
    
    except requests.exceptions.RequestException as e:
        print(f"Exception in get_slave_reply: {str(e)}")
        return {}

def write_raw_data_to_file():
    global all_reply

    # 获取当前时间
    current_time = datetime.now()

    # 格式化日期时间字符串，替换非法字符
    stop_time = current_time.strftime("%Y-%m-%d_%H-%M-%S")

    # 写入JSON文件
    with open(f"./revolutionB/米游社_{passageid}_{stop_time}_抓取结果.json", "w", encoding="utf-8") as json_file:
        json.dump(all_reply, json_file, ensure_ascii=False, indent=4)

    # 统计回复总数，包括子回复
    total_replies = sum(len(reply["slave_reply"]) + 1 for reply in all_reply.values())
    print(f"Total replies (including sub-replies): {total_replies}")

    # 过滤和排序统计结果
    filtered_counts = {
        "ip_region_counts": {k: v for k, v in ip_region_counts.items() if v >= 2},
        "nickname_counts": {k: v for k, v in nickname_counts.items() if v >= 2},
        "level_counts": {k: v for k, v in level_counts.items() if v >= 2},
        "content_counts": {k: v for k, v in content_counts.items() if v >= 2},
    }

    # 按值的大小从大到小排序
    sorted_counts = {
        key: OrderedDict(sorted(value.items(), key=lambda item: item[1], reverse=True))
        for key, value in filtered_counts.items()
    }

    # 写入统计结果文件
    statistics = {
        "filtered_counts": filtered_counts,
        "sorted_counts": sorted_counts,
        "total_replies": total_replies
    }

    with open(f"./revolutionB/米游社_{passageid}_{stop_time}_抓取结果统计.json", "w", encoding="utf-8") as stat_file:
        json.dump(statistics, stat_file, ensure_ascii=False, indent=4)

def main():
    # 创建线程
    threads = []
    num_threads = 72  # 设置合适的线程数

    for i in range(num_threads):
        thread = threading.Thread(target=fetch_data, args=(i,))
        time.sleep(0.75)
        thread.start()
        threads.append(thread)
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()

    # 数据抓取完成后写入抓取结果文件和统计文件
    write_raw_data_to_file()

    print("所有数据处理完成")

if __name__ == "__main__":
    main()
