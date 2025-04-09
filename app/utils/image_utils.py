import os
import shutil
from typing import Optional, List, Tuple
from pathlib import Path
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.utils.helpers import generate_unique_filename
from app.core.config import settings

# Максимальные размеры изображений для разных категорий
IMAGE_SIZES = {
    "thumbnail": (150, 150),
    "medium": (400, 400),
    "large": (800, 800)
}

# Допустимые типы изображений
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]

async def save_upload_file(
    upload_file: UploadFile, 
    folder: str = "products"
) -> Optional[str]:
    """
    Сохраняет загруженный файл в указанную папку и возвращает относительный путь
    
    Args:
        upload_file: Загруженный файл
        folder: Подпапка в директории медиафайлов (по умолчанию "products")
    
    Returns:
        Optional[str]: Относительный путь к сохраненному файлу или None при ошибке
    """
    # Проверяем тип файла
    if upload_file.content_type not in ALLOWED_IMAGE_TYPES:
        return None
    
    # Создаем уникальное имя файла
    filename = generate_unique_filename(upload_file.filename)
    
    # Создаем путь для сохранения файла
    save_dir = Path(settings.MEDIA_DIR) / folder
    save_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = save_dir / filename
    
    # Сохраняем файл
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    except Exception:
        return None
    finally:
        await upload_file.close()
    
    # Возвращаем относительный путь
    return str(Path(folder) / filename)

def create_image_variations(
    image_path: str, 
    sizes: List[Tuple[str, Tuple[int, int]]] = None
) -> List[str]:
    """
    Создает варианты изображения разных размеров и возвращает их пути
    
    Args:
        image_path: Путь к исходному изображению
        sizes: Список кортежей (суффикс, (ширина, высота))
    
    Returns:
        List[str]: Список путей к созданным вариантам изображений
    """
    if sizes is None:
        sizes = [
            ("thumbnail", IMAGE_SIZES["thumbnail"]),
            ("medium", IMAGE_SIZES["medium"]),
        ]
    
    full_path = Path(settings.MEDIA_DIR) / image_path
    
    if not full_path.exists():
        return []
    
    try:
        # Открываем исходное изображение
        with Image.open(full_path) as img:
            # Создаем варианты изображений
            variations = []
            
            for suffix, size in sizes:
                # Создаем имя файла для варианта
                path = full_path.parent / f"{full_path.stem}_{suffix}{full_path.suffix}"
                
                # Изменяем размер и сохраняем
                img_copy = img.copy()
                img_copy.thumbnail(size, Image.LANCZOS)
                img_copy.save(path)
                
                # Добавляем путь к результату
                rel_path = str(Path(image_path).parent / f"{full_path.stem}_{suffix}{full_path.suffix}")
                variations.append(rel_path)
            
            return variations
    
    except (UnidentifiedImageError, OSError):
        return []

def delete_image_with_variations(image_path: str) -> bool:
    """
    Удаляет изображение и все его варианты
    
    Args:
        image_path: Путь к исходному изображению
    
    Returns:
        bool: Успешно ли удалены файлы
    """
    full_path = Path(settings.MEDIA_DIR) / image_path
    
    if not full_path.exists():
        return False
    
    # Удаляем основное изображение
    deleted = []
    try:
        os.remove(full_path)
        deleted.append(str(full_path))
    except OSError:
        pass
    
    # Ищем и удаляем варианты изображений
    for suffix in ["thumbnail", "medium", "large"]:
        variation_path = full_path.parent / f"{full_path.stem}_{suffix}{full_path.suffix}"
        try:
            if variation_path.exists():
                os.remove(variation_path)
                deleted.append(str(variation_path))
        except OSError:
            pass
    
    return len(deleted) > 0