"""
Redis client for the document processor service.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisClient:
    """Client for Redis operations."""

    def __init__(self, redis_url: str):
        """
        Initialize Redis client.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            await self.client.ping()
            logger.info("Redis connection initialized")
        except Exception as e:
            logger.error(f"Error initializing Redis connection: {str(e)}")
            raise

    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def set_cache(
        self, key: str, value: Union[str, Dict, List], expiry: int = 3600
    ) -> bool:
        """
        Set a cache value.

        Args:
            key: Cache key
            value: Value to cache
            expiry: Expiry time in seconds

        Returns:
            bool: True if set successfully, False otherwise
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return False

        try:
            # Convert dict/list to JSON string
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            await self.client.set(key, value, ex=expiry)
            return True
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {str(e)}")
            return False

    async def get_cache(
        self, key: str, as_json: bool = True
    ) -> Optional[Union[str, Dict, List]]:
        """
        Get a cache value.

        Args:
            key: Cache key
            as_json: Whether to parse the value as JSON

        Returns:
            Optional[Union[str, Dict, List]]: Cached value if found, None otherwise
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return None

        try:
            value = await self.client.get(key)
            if value and as_json:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return value
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {str(e)}")
            return None

    async def delete_cache(self, key: str) -> bool:
        """
        Delete a cache value.

        Args:
            key: Cache key

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return False

        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting cache for key {key}: {str(e)}")
            return False

    async def add_to_queue(self, queue_name: str, item: Union[str, Dict]) -> bool:
        """
        Add an item to a queue.

        Args:
            queue_name: Queue name
            item: Item to add

        Returns:
            bool: True if added successfully, False otherwise
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return False

        try:
            # Convert dict to JSON string
            if isinstance(item, dict):
                item = json.dumps(item)

            await self.client.lpush(queue_name, item)
            return True
        except Exception as e:
            logger.error(f"Error adding item to queue {queue_name}: {str(e)}")
            return False

    async def get_from_queue(
        self, queue_name: str, as_json: bool = True, timeout: int = 0
    ) -> Optional[Union[str, Dict]]:
        """
        Get an item from a queue.

        Args:
            queue_name: Queue name
            as_json: Whether to parse the item as JSON
            timeout: Timeout in seconds (0 for no blocking)

        Returns:
            Optional[Union[str, Dict]]: Queue item if found, None otherwise
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return None

        try:
            if timeout > 0:
                # Blocking pop from the right
                result = await self.client.brpop(queue_name, timeout=timeout)
                if result:
                    _, item = result
                else:
                    return None
            else:
                # Non-blocking pop from the right
                item = await self.client.rpop(queue_name)

            if item and as_json:
                try:
                    return json.loads(item)
                except json.JSONDecodeError:
                    return item
            return item
        except Exception as e:
            logger.error(f"Error getting item from queue {queue_name}: {str(e)}")
            return None 