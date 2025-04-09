import os
import re
import uuid
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

def slugify(value: str) -> str:
    """
    Преобразует строку в URL-slug.
    Например: "Привет мир!" -> "privet-mir"
    """
    # Нормализация и преобразование в ASCII
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    # Удаление всех символов, которые не являются буквенно-цифровыми, подчеркиванием или дефисом
    value = re.sub(r'[^\w\s-]', '', value.lower())
    # Замена всех пробелов на дефисы
    value = re.sub(r'[-\s]+', '-', value).strip('-_')
    return value

def generate_unique_filename(filename: str) -> str:
    """
    Генерирует уникальное имя файла на основе оригинального имени и UUID
    """
    # Разделяем имя файла и расширение
    name, ext = os.path.splitext(filename)
    # Генерируем slug из имени файла
    name_slug = slugify(name)
    # Добавляем UUID для уникальности
    unique_id = str(uuid.uuid4())[:8]
    # Добавляем текущую дату в формате YYYYMMDD
    date_str = datetime.now().strftime("%Y%m%d")
    # Собираем новое имя файла
    return f"{name_slug}-{date_str}-{unique_id}{ext}"

def paginate_results(
    items: List[Any], 
    page: int = 1, 
    page_size: int = 10
) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Разбивает список элементов на страницы и возвращает текущую страницу
    вместе с метаданными для пагинации
    """
    # Проверка корректности параметров
    page = max(1, page)
    page_size = max(1, min(100, page_size))  # Ограничиваем размер страницы от 1 до 100
    
    # Вычисляем начальный и конечный индексы
    start = (page - 1) * page_size
    end = start + page_size
    
    # Получаем элементы текущей страницы
    paginated_items = items[start:end]
    
    # Вычисляем общее количество страниц
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size  # Округление вверх
    
    # Собираем метаданные пагинации
    pagination_meta = {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_previous": page > 1,
        "has_next": page < total_pages,
    }
    
    return paginated_items, pagination_meta

def filter_dict_keys(data: Dict[str, Any], allowed_keys: List[str]) -> Dict[str, Any]:
    """
    Фильтрует словарь, оставляя только разрешенные ключи
    """
    return {key: value for key, value in data.items() if key in allowed_keys}

def parse_filters_from_query_params(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Преобразует параметры запроса в словарь фильтров для запросов к БД
    """
    filters = {}
    
    # Обработка простых фильтров (точное совпадение)
    exact_match_params = ["category_id", "catalog_id", "manufacturer_id", "in_stock"]
    for param in exact_match_params:
        if param in query_params and query_params[param] is not None:
            filters[param] = query_params[param]
    
    # Обработка фильтров по диапазону
    range_params = [
        ("min_price", "price__gte"),
        ("max_price", "price__lte"),
    ]
    for query_param, filter_param in range_params:
        if query_param in query_params and query_params[query_param] is not None:
            filters[filter_param] = query_params[query_param]
    
    # Обработка поиска по тексту
    if "search" in query_params and query_params["search"]:
        filters["search"] = query_params["search"]
    
    return filters