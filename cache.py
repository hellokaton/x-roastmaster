import sqlite3
import time
import json
from typing import Dict, Any, Optional

from logger import logger


class SQLiteCache:
    """基于SQLite的缓存实现，支持过期时间设置"""
    
    def __init__(self, db_path: str = "twitter_cache.db", expire_minutes: int = 30):
        """
        初始化SQLite缓存
        
        :param db_path: SQLite数据库文件路径
        :param expire_minutes: 缓存过期时间(分钟)，默认30分钟
        """
        self.db_path = db_path
        self.expire_minutes = expire_minutes
        # 转换为秒存储便于计算
        self.expire_seconds = expire_minutes * 60
        self._init_db()
        logger.info(f"缓存初始化完成，使用数据库: {db_path}，过期时间: {expire_minutes}分钟")
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS twitter_cache (
            cache_key TEXT PRIMARY KEY,
            data TEXT,
            timestamp INTEGER
        )
        ''')
        conn.commit()
        conn.close()
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取数据
        
        :param cache_key: 缓存键
        :return: 缓存的数据，如果不存在或已过期则返回None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT data, timestamp FROM twitter_cache WHERE cache_key = ?", (cache_key,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            data_str, timestamp = result
            cached_seconds = int(time.time() - timestamp)
            cached_minutes = cached_seconds // 60
            cached_seconds_remainder = cached_seconds % 60
            
            # 检查是否过期
            if time.time() - timestamp < self.expire_seconds:
                logger.debug(f"缓存命中: {cache_key} (已缓存{cached_minutes}分{cached_seconds_remainder}秒)")
                return json.loads(data_str)
            else:
                # 数据已过期，删除缓存
                logger.debug(f"缓存已过期: {cache_key} (已缓存{cached_minutes}分{cached_seconds_remainder}秒，超过{self.expire_minutes}分钟)")
                self.delete(cache_key)
        else:
            logger.debug(f"缓存未命中: {cache_key}")
        return None
    
    def set(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        设置缓存数据
        
        :param cache_key: 缓存键
        :param data: 要缓存的数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO twitter_cache VALUES (?, ?, ?)",
            (cache_key, json.dumps(data), int(time.time()))
        )
        conn.commit()
        conn.close()
        logger.debug(f"已写入缓存: {cache_key} (过期时间: {self.expire_minutes}分钟)")
    
    def delete(self, cache_key: str) -> None:
        """
        删除缓存数据
        
        :param cache_key: 缓存键
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM twitter_cache WHERE cache_key = ?", (cache_key,))
        conn.commit()
        conn.close()
        logger.debug(f"已删除缓存: {cache_key}")
    
    def clear_expired(self) -> None:
        """清除所有过期的缓存数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取过期条目数量
        expire_time = int(time.time() - self.expire_seconds)
        cursor.execute("SELECT COUNT(*) FROM twitter_cache WHERE timestamp < ?", (expire_time,))
        count = cursor.fetchone()[0]
        
        # 删除过期条目
        if count > 0:
            cursor.execute(
                "DELETE FROM twitter_cache WHERE timestamp < ?", 
                (expire_time,)
            )
            conn.commit()
            logger.info(f"已清除 {count} 条过期缓存 (超过{self.expire_minutes}分钟)")
        
        conn.close()
    
    def clear_all(self) -> None:
        """清除所有缓存数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取条目数量
        cursor.execute("SELECT COUNT(*) FROM twitter_cache")
        count = cursor.fetchone()[0]
        
        # 删除所有条目
        cursor.execute("DELETE FROM twitter_cache")
        conn.commit()
        conn.close()
        
        logger.info(f"已清除所有 {count} 条缓存")


class NullCache:
    """空缓存实现，用于禁用缓存时"""
    
    def __init__(self):
        logger.info("缓存已禁用，使用空缓存实现")
    
    def get(self, cache_key: str) -> None:
        logger.debug(f"缓存已禁用，跳过读取: {cache_key}")
        return None
    
    def set(self, cache_key: str, data: Dict[str, Any]) -> None:
        logger.debug(f"缓存已禁用，跳过写入: {cache_key}")
        pass
    
    def delete(self, cache_key: str) -> None:
        pass
    
    def clear_expired(self) -> None:
        pass
    
    def clear_all(self) -> None:
        pass 