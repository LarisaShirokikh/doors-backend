import json
from typing import Any, Optional, Union
import redis
from app.core.config import settings

# Создание подключения к Redis
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True  # Автоматически декодировать байты в строки
)

def set_cache(key: str, value: Any, expiration: int = 3600) -> bool:
    """
    Сохранить данные в кэш Redis
    
    Args:
        key: Ключ для сохранения
        value: Значение для сохранения (будет сериализовано в JSON)
        expiration: Время хранения в секундах (по умолчанию 1 час)
    
    Returns:
        bool: Успешно ли сохранены данные
    """
    try:
        # Сериализация данных в JSON
        serialized_value = json.dumps(value)
        
        # Сохранение в Redis с указанным временем жизни
        redis_client.setex(key, expiration, serialized_value)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении в кэш: {e}")
        return False

def get_cache(key: str) -> Optional[Any]:
    """
    Получить данные из кэша Redis
    
    Args:
        key: Ключ для поиска
    
    Returns:
        Any or None: Десериализованные данные или None, если ключ не найден
    """
    try:
        # Получение данных из Redis
        data = redis_client.get(key)
        
        if data is None:
            return None
        
        # Десериализация данных из JSON
        return json.loads(data)
    except Exception as e:
        print(f"Ошибка при получении из кэша: {e}")
        return None

def delete_cache(key: str) -> bool:
    """
    Удалить данные из кэша Redis
    
    Args:
        key: Ключ для удаления
    
    Returns:
        bool: Успешно ли удалены данные
    """
    try:
        # Удаление ключа из Redis
        return redis_client.delete(key) > 0
    except Exception as e:
        print(f"Ошибка при удалении из кэша: {e}")
        return False

def flush_pattern(pattern: str) -> int:
    """
    Удалить все ключи, соответствующие шаблону
    
    Args:
        pattern: Шаблон для поиска ключей (например, "products:*")
    
    Returns:
        int: Количество удаленных ключей
    """
    try:
        # Поиск ключей по шаблону
        keys = redis_client.keys(pattern)
        
        if not keys:
            return 0
        
        # Удаление найденных ключей
        return redis_client.delete(*keys)
    except Exception as e:
        print(f"Ошибка при очистке кэша по шаблону: {e}")
        return 0

def clear_all_cache() -> bool:
    """
    Очистить весь кэш Redis
    
    Returns:
        bool: Успешно ли очищен кэш
    """
    try:
        # Очистка всех данных в текущей базе данных Redis
        redis_client.flushdb()
        return True
    except Exception as e:
        print(f"Ошибка при очистке всего кэша: {e}")
        return False

def increment_counter(key: str, amount: int = 1, expiration: int = None) -> int:
    """
    Увеличить счетчик
    
    Args:
        key: Ключ счетчика
        amount: Значение для увеличения (по умолчанию 1)
        expiration: Время жизни ключа в секундах (по умолчанию бессрочно)
    
    Returns:
        int: Новое значение счетчика
    """
    try:
        # Увеличение счетчика
        new_value = redis_client.incrby(key, amount)
        
        # Установка времени жизни, если указано
        if expiration is not None:
            redis_client.expire(key, expiration)
            
        return new_value
    except Exception as e:
        print(f"Ошибка при увеличении счетчика: {e}")
        return 0