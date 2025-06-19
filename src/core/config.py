import yaml
from dotmap import DotMap
from pathlib import Path

def load_config(config_path: str) -> DotMap:
    """
    Загружает конфигурационный файл YAML и возвращает его в виде объекта DotMap.

    Args:
        config_path: Путь к файлу конфигурации.

    Returns:
        DotMap: Объект DotMap с данными конфигурации.
        
    Raises:
        FileNotFoundError: Если файл конфигурации не найден.
        yaml.YAMLError: Если произошла ошибка при парсинге YAML.
    """
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл конфигурации не найден по пути: {config_path}")
        
    with open(path, 'r', encoding='utf-8') as f:
        try:
            config_data = yaml.safe_load(f)
            return DotMap(config_data)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Ошибка парсинга YAML в файле {config_path}: {e}") 