import requests
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import time

def fetch_comments(api_url, timeout=5, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(api_url, timeout=timeout)
            if response.status_code == 200:
                json_data = response.json()
                if json_data.get('retcode') == 2110:
                    print(f"评论已折叠: {json_data.get('message')}")
                    return None
                return json_data
            else:
                print(f"无法获取数据. 服务器返回: {response.status_code}")
        except requests.exceptions.Timeout:
            print(f"请求超时. 将在 3 秒后重试... (第 {attempt+1} 次重试)")
            time.sleep(3)
        except requests.exceptions.ConnectionError as e:
            print(f"连接错误: {e}. 将在 15 秒后重试... (第 {attempt+1} 次重试)")
            time.sleep(15)
        except requests.exceptions.HTTPError as e:
            print(f"HTTP错误: {e}. 将在 15 秒后重试... (第 {attempt+1} 次重试)")
            time.sleep(15)
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {e}. 将在 15 秒后重试... (第 {attempt+1} 次重试)")
            time.sleep(15)
    return None

def extract_comment_info(comment):
    reply = comment['reply']
    user = comment['user']
    created_at = datetime.fromtimestamp(reply['created_at']).strftime('%Y-%m-%d %H:%M:%S')
    return {
        'reply_id': reply['reply_id'],
        '米游社ID': user['uid'],
        '米游社昵称': user['nickname'],
        '米游社等级': user['level_exp']['level'],
        '经验': user['level_exp']['exp'],
        '来自': user['ip_region'],
        '评论内容': reply['content'],
        '点赞数': comment['stat']['like_num'],
        '发布时间': created_at,
        'floor_id': reply.get('floor_id', None),
        '父回复ID': reply['f_reply_id']
    }

def save_to_csv(data, filename, fieldnames):
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        dict_writer.writerows(data)

def fetch_and_process_comments(last_id, api_url_template, seen_comments, floor_reply_count, post_id):
    api_url = api_url_template.format(last_id, post_id)
    comments_data = fetch_comments(api_url)
    if comments_data and 'data' in comments_data:
        comments_list = comments_data['data']['list']
        new_comments = []
        for comment in comments_list:
            comment_info = extract_comment_info(comment)
            if comment_info['reply_id'] not in seen_comments:
                seen_comments.add(comment_info['reply_id'])
                new_comments.append(comment_info)
                if comment.get('sub_replies'):
                    floor_id = comment_info['floor_id']
                    if floor_id:
                        sub_replies = fetch_sub_replies(floor_id, post_id)
                        floor_reply_count[floor_id] += len(sub_replies)
                        new_comments.extend(sub_replies)
        return new_comments
    return []

def fetch_sub_replies(floor_id, post_id, retries=3):
    sub_comments = []
    last_id = 0
    sub_api_url_template = "https://bbs-api.miyoushe.com/post/wapi/getSubReplies?floor_id={}&gids=5&post_id={}&size=50"
    sub_api_paged_url_template = "https://bbs-api.miyoushe.com/post/wapi/getSubReplies?floor_id={}&gids=5&last_id={}&post_id={}&size=50"
    
    retry_count = 0
    while retry_count < retries:
        if last_id == 0:
            sub_api_url = sub_api_url_template.format(floor_id, post_id)
        else:
            sub_api_url = sub_api_paged_url_template.format(floor_id, last_id, post_id)
            
        sub_comments_data = fetch_comments(sub_api_url)
        if sub_comments_data and 'data' in sub_comments_data:
            sub_comments_list = sub_comments_data['data']['list']
            for sub_comment in sub_comments_list:
                sub_comment_info = extract_comment_info(sub_comment)
                sub_comments.append(sub_comment_info)
            last_id = sub_comments_data['data'].get('last_id')
            if sub_comments_data['data'].get('is_last', True):
                break
        elif sub_comments_data is None:
            retry_count += 1
            print(f"无法获取子回复数据，楼层ID: {floor_id}，重试 {retry_count}/{retries}")
            time.sleep(3)
        else:
            break

    if retry_count == retries:
        print(f"超过最大重试次数，丢弃楼层ID: {floor_id} 的子回复数据")

    return sub_comments

def fetch_missing_floor_replies(missing_floors, post_id, workers):
    all_missing_replies = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_floor = {executor.submit(fetch_sub_replies, floor_id, post_id): floor_id for floor_id in missing_floors}
        for future in tqdm(as_completed(future_to_floor), total=len(future_to_floor), desc="正在抓取被删除楼层内回复", unit="层"):
            floor_id = future_to_floor[future]
            try:
                sub_replies = future.result()
                all_missing_replies.extend(sub_replies)
            except Exception as exc:
                print(f"楼层ID {floor_id} 的子回复抓取时发生异常: {exc}")
    return all_missing_replies

def main(post_id, last_id_end, workers):
    api_url_template = "https://bbs-api.miyoushe.com/post/wapi/getPostReplies?gids=5&is_hot=false&order_type=1&last_id={}&post_id={}&size=50"
    all_comments = []
    seen_comments = set()
    floor_reply_count = defaultdict(int)  # 用于统计每个楼层的子回复数

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_and_process_comments, last_id, api_url_template, seen_comments, floor_reply_count, post_id) for last_id in range(0, last_id_end)]
        for future in tqdm(as_completed(futures), total=len(futures), desc="拉取评论内容中..."):
            result = future.result()
            if result:
                all_comments.extend(result)

    # 找出缺失的楼层ID
    floor_ids = set([comment['floor_id'] for comment in all_comments if comment['floor_id'] is not None])
    missing_floors = set(range(1, max(floor_ids) + 1)) - floor_ids

    print(f"缺失的楼层数量: {len(missing_floors)}")

    # 抓取缺失楼层的子回复
    missing_replies = fetch_missing_floor_replies(missing_floors, post_id, workers)
    all_comments.extend(missing_replies)

    save_to_csv(all_comments, '米游社.csv', all_comments[0].keys())

    # 生成楼层子回复统计数据并保存
    floor_data = [{'楼层ID': floor_id, '子回复数量': count} for floor_id, count in floor_reply_count.items()]
    save_to_csv(floor_data, '楼层子回复统计.csv', ['楼层ID', '子回复数量'])

    # 生成评论地区分布CSV
    region_distribution = defaultdict(int)
    for comment in all_comments:
        region_distribution[comment['来自']] += 1
    region_data = [{'地区': region, '评论次数': count} for region, count in region_distribution.items()]
    save_to_csv(region_data, '评论地区分布.csv', ['地区', '评论次数'])

    # 生成评论用户信息CSV
    user_comment_count = defaultdict(int)
    for comment in all_comments:
        user_comment_count[comment['米游社昵称']] += 1
    user_data = [{'米游社昵称': user, '评论次数': count} for user, count in user_comment_count.items()]
    save_to_csv(user_data, '评论用户信息.csv', ['米游社昵称', '评论次数'])
    print("评论信息已成功保存到 米游社.csv")

if __name__ == "__main__":
    post_id = input("请输入文章ID: ")
    last_id_end = int(input("请输入分页结束值: "))
    workers = int(input("请输入运行线程，取值范围1-64: "))
    main(post_id, last_id_end, workers)
