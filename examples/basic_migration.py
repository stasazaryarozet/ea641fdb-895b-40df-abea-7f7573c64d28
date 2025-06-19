#!/usr/bin/env python3
"""
Пример использования Tilda Migration Agent
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.agent import MigrationAgent
from core.config import Config
from utils.logger import setup_logging


def main():
    """Пример полной миграции"""
    
    # Настройка логирования
    setup_logging("logs/example.log", "INFO")
    
    try:
        # Загрузка конфигурации
        config = Config("config.yaml")
        
        # Создание агента
        agent = MigrationAgent(config, dry_run=False)
        
        # Запуск миграции
        print("🚀 Запуск примера миграции...")
        agent.run()
        
        print("✅ Миграция завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


def extract_only_example():
    """Пример только извлечения данных"""
    
    setup_logging("logs/extract_example.log", "INFO")
    
    try:
        config = Config("config.yaml")
        agent = MigrationAgent(config)
        
        print("📥 Извлечение данных с Tilda...")
        agent.extract_only()
        
        print("✅ Извлечение завершено!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


def deploy_only_example():
    """Пример только развертывания"""
    
    setup_logging("logs/deploy_example.log", "INFO")
    
    try:
        config = Config("config.yaml")
        agent = MigrationAgent(config)
        
        print("☁️ Развертывание на Google Cloud...")
        agent.deploy_only()
        
        print("✅ Развертывание завершено!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Пример использования Tilda Migration Agent")
    parser.add_argument("--mode", choices=["full", "extract", "deploy"], 
                       default="full", help="Режим работы")
    
    args = parser.parse_args()
    
    if args.mode == "full":
        main()
    elif args.mode == "extract":
        extract_only_example()
    elif args.mode == "deploy":
        deploy_only_example() 