from typing import Dict, Any, Optional

import requests

from config import X_API_KEY, ENABLE_CACHE, CACHE_EXPIRE_MINUTES
from cache import SQLiteCache, NullCache
from logger import logger


class TwitterAPI:
    BASE_URL = "https://api.twitterapi.io/twitter"

    def __init__(self, _api_key: str, use_cache: bool = None):
        self._api_key = _api_key
        self._headers = {"X-API-Key": _api_key}
        
        # 初始化缓存，优先使用参数传递的值，其次使用配置文件值
        if use_cache is None:
            use_cache = ENABLE_CACHE
            
        if use_cache:
            self.cache = SQLiteCache(db_path="twitter_cache.db", expire_minutes=CACHE_EXPIRE_MINUTES)
        else:
            self.cache = NullCache()

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """发送请求并处理标准响应格式"""
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, headers=self._headers, params=params)
            response.raise_for_status()  # 如果响应状态码不是 200，抛出异常

            data = response.json()
            if data["status"] != "success":
                raise Exception(f"API 错误: {data['msg']}")

            return data["data"]
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求错误: {str(e)}")
        except ValueError:
            raise Exception("无法解析 JSON 响应")

    def user_info(self, username: str) -> Dict[str, Any]:
        """获取用户信息"""
        # 生成缓存键
        cache_key = f"user_info:{username}"
        
        # 尝试从缓存获取数据
        cached_data = self.cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存读取用户信息: @{username}")
            return cached_data
        
        # 缓存未命中，发起API请求
        logger.info(f"缓存未命中，正在请求用户信息: @{username}")
        data = self._make_request("user/info", params={"userName": username})
        
        # 存储到缓存
        self.cache.set(cache_key, data)
        
        return data

    def user_tweets(self, user_id: str, cursor: str = "") -> Dict[str, Any]:
        """获取用户推文"""
        # 生成缓存键
        cache_key = f"user_tweets:{user_id}:{cursor}"
        
        # 尝试从缓存获取数据
        cached_data = self.cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存读取用户推文: 用户ID {user_id}")
            return cached_data
        
        # 缓存未命中，发起API请求
        logger.info(f"缓存未命中，正在请求用户推文: 用户ID {user_id}")
        data = self._make_request("user/last_tweets", params={"userId": user_id, "cursor": cursor})
        
        # 存储到缓存
        self.cache.set(cache_key, data)
        
        return data
