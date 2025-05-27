# app/utils/converters.py
from typing import List, Dict, Any, Optional, Type, TypeVar, Union
from sqlalchemy.orm import Session
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def model_to_schema(model: Any, schema_class: Type[T]) -> T:
    """Преобразование модели SQLAlchemy в схему Pydantic"""
    return schema_class.from_attributes(model)

def model_list_to_schema(models: List[Any], schema_class: Type[T]) -> List[T]:
    """Преобразование списка моделей SQLAlchemy в список схем Pydantic"""
    return [model_to_schema(model, schema_class) for model in models]

def paginated_response(
    items: List[Any], 
    schema_class: Type[T], 
    total: int, 
    page: int, 
    per_page: int
) -> Dict[str, Any]:
    """Создание ответа с пагинацией"""
    total_pages = (total + per_page - 1) // per_page
    return {
        "items": model_list_to_schema(items, schema_class),
        "total": total,
        "page": page,
        "perPage": per_page,
        "totalPages": total_pages
    }

def calculate_products_count(items: List[Any]) -> List[Dict[str, Any]]:
    """Подсчет количества товаров для категорий, брендов и т.д."""
    result = []
    for item in items:
        item_dict = item.__dict__.copy()
        if hasattr(item, "products"):
            item_dict["products_count"] = len(item.products)
        result.append(item_dict)
    return result

def camelcase_keys(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Преобразование ключей snake_case в camelCase для API"""
    if isinstance(data, list):
        return [camelcase_keys(item) for item in data]
    
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            value = camelcase_keys(value)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            value = camelcase_keys(value)
        
        # Преобразование snake_case в camelCase
        if "_" in key:
            words = key.split("_")
            camel_key = words[0] + "".join(word.capitalize() for word in words[1:])
            result[camel_key] = value
        else:
            result[key] = value
    
    return result