# -*- coding: utf-8 -*-

import argparse
import json
import re
import sys
import time

from openai import OpenAI

from config import OPENAI_URL, OPENAI_KEY, OPENAI_MODEL, X_API_KEY
from logger import logger
from x_api import TwitterAPI

# 确保终端支持UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')


# 清理文本，移除链接和emoji
def clean_text(text):
    """移除文本中的所有特殊字符，只保留安全的ASCII字符和UTF-8文本"""
    if not text:
        return ""

    # 移除Twitter链接
    text = re.sub(r'https://t\.co/\w+', '', text)

    # 移除连续的空白字符
    text = re.sub(r'\s+', ' ', text)

    # 将无法用JSON安全传输的字符转换为安全形式
    # 使用Python的repr()函数转换文本，然后去除引号
    safe_text = repr(text).strip("'\"")

    # 去除转义序列，如果有的话
    if safe_text.startswith("u'") or safe_text.startswith('u"'):
        safe_text = safe_text[2:-1]
    elif safe_text.startswith("'") or safe_text.startswith('"'):
        safe_text = safe_text[1:-1]

    # 去除首尾空白符
    safe_text = safe_text.strip()

    return safe_text


def fetch_user_data(api, user_login):
    """获取Twitter用户数据和推文"""
    logger.info(f'开始获取用户 {user_login} 的数据')

    # 先获取用户信息
    start_time = time.time()
    user_info = api.user_info(user_login)
    user_info_time = time.time() - start_time

    uid = user_info['id']
    description = clean_text(user_info.get('description', ''))

    # 获取用户推文
    start_time = time.time()
    tweets_data = api.user_tweets(uid)
    tweets_time = time.time() - start_time

    # 筛选推文
    tweets_filtered = []

    # 如果有置顶推文，加入列表
    if "pin_tweet" in tweets_data and tweets_data["pin_tweet"]:
        if "text" in tweets_data["pin_tweet"]:
            tweets_filtered.append(clean_text(tweets_data["pin_tweet"]["text"]))

    # 添加普通推文
    if "tweets" in tweets_data and tweets_data["tweets"]:
        for tweet in tweets_data["tweets"]:
            if tweet.get("type") == "tweet" and "text" in tweet:
                tweets_filtered.append(clean_text(tweet["text"]))

    # 获取前 10 条
    tweets_filtered = tweets_filtered[:10]

    logger.info(f"获取数据耗时: 用户信息 {user_info_time:.3f}秒, 推文 {tweets_time:.3f}秒")

    return {
        "username": user_login,
        "description": description,
        "tweets": tweets_filtered
    }


def analyze_user(user_data):
    """使用AI分析用户数据"""
    client = OpenAI(base_url=OPENAI_URL, api_key=OPENAI_KEY)

    # 构建系统提示词 - 使用纯ASCII字符
    system_prompt = """
    你是个混迹社交媒体的毒舌点评师，擅长用最生猛的大白话戳穿用户本质。给老子好好分析：

    任务要求:
    1. 用街头巷尾的大白话分析，禁止学术用语
    2. 吐槽要带刺但藏着糖，骂中带夸才是真本事
    3. 脏话要像辣椒面——提味但不烧胃
    4. 必须基于真实数据，别他妈瞎编

    输出要求:
    1. 基本特征：3-5个带脏字的特征词（例：他妈的/屌毛/装逼犯）
    2. 人物解析：100字左右，要像兄弟聊天那样直白（例："这货表面装高冷，骨子里就是个...")
    3. 辛辣点评：100字内暴击彩虹屁，必须包含至少3个脏话+3个夸奖（例："你他妈真是个自恋的戏精，但老子就欣赏你这股不要脸的劲儿！"）

    特别提醒:
    - 脏话要用得俏皮，禁止人身攻击
    - 夸要夸到心坎里，骂要骂在痛点上
    - 学习祖安文化精髓，保持阴阳怪气的幽默感
    - 每句脏话后面必须跟三个彩虹屁作为补偿
    - 直接输出结果，不做任何解释
    """

    # 将tweets数组转成字符串，确保字符安全
    safe_tweets = []
    for i, tweet in enumerate(user_data['tweets']):
        if tweet and tweet.strip():  # 确保推文不为空
            safe_tweets.append(f"{i + 1}. {tweet}")

    tweets_text = "\n".join(safe_tweets)

    # 构建用户提示词 - 使用纯ASCII字符
    user_prompt = f"""
    请基于以下Twitter用户数据进行分析和辛辣点评：
    用户简介: {user_data['description']}
    最近推文:
    {tweets_text}
    """

    try:
        # 使用纯ASCII编码的消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # 确保JSON兼容性
        messages_json = json.dumps(messages, ensure_ascii=True)
        messages = json.loads(messages_json)

        completion = client.chat.completions.create(
            extra_headers={
                "X-Title": "Twitter User Analysis Tool",
            },
            model=OPENAI_MODEL,
            messages=messages,
        )

        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"AI分析过程出错: {str(e)}")
        logger.error(f"系统提示词: {repr(system_prompt)}")
        logger.error(f"用户提示词: {repr(user_prompt)}")
        return "无法完成分析，可能是因为输入数据包含特殊字符或API调用失败。"


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Twitter用户分析工具')
    parser.add_argument('--username', '-u', type=str, help='要分析的Twitter用户名')
    parser.add_argument('--no-cache', action='store_true', help='禁用缓存功能')
    parser.add_argument('--clear-cache', action='store_true', help='清除缓存后再运行')
    args = parser.parse_args()

    try:
        # 确定是否使用缓存
        use_cache = not args.no_cache

        # 初始化Twitter API
        api = TwitterAPI(X_API_KEY, use_cache=use_cache)

        # 如果需要清除缓存
        if args.clear_cache and use_cache:
            logger.info("正在清除缓存...")
            api.cache.clear_all()
            logger.info("缓存已清除")

        # 获取用户名
        user_login = args.username or input("请输入要分析的Twitter用户名(默认hellokaton): ") or "hellokaton"

        # 记录缓存状态
        cache_status = "已启用" if use_cache else "已禁用"
        logger.info(f"缓存状态: {cache_status}")

        # 获取用户数据
        user_data = fetch_user_data(api, user_login)

        logger.info(f"获取到用户 @{user_data['username']} 的数据")
        logger.info(f"用户简介: {user_data['description']}")
        logger.info(f"获取到最新 {len(user_data['tweets'])} 条推文")

        # 分析用户
        logger.info("正在用祖安模式分析用户数据...")
        analysis = analyze_user(user_data)

        logger.info("毒舌点评生成完毕:\n" + analysis)

    except Exception as e:
        logger.error(f"发生错误: {str(e)}")


if __name__ == "__main__":
    main()
