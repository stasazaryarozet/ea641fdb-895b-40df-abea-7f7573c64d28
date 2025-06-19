#!/usr/bin/env python3
"""
Tilda to Google Cloud Migration Agent
Автономный ИИ-агент для переноса сайтов с Tilda на Google Cloud
"""

import click
import sys
from pathlib import Path

# Добавляем src в путь для импортов
sys.path.insert(0, str(Path(__file__).parent))

from core.agent import MigrationAgent
from core.config import Config
from utils.logger import setup_logging


@click.group()
@click.version_option()
def cli():
    """Tilda to Google Cloud Migration Agent"""
    pass


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
@click.option('--dry-run', is_flag=True, help='Run without making actual changes')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def migrate(config, dry_run, verbose):
    """Запустить полную миграцию сайта с Tilda на Google Cloud"""
    try:
        # Загружаем конфигурацию
        cfg = Config(config)
        
        # Настраиваем логирование
        log_level = "DEBUG" if verbose else cfg.logging.level
        setup_logging(cfg.logging.file, log_level)
        
        # Создаем и запускаем агента
        agent = MigrationAgent(cfg, dry_run=dry_run)
        agent.run()
        
    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
def extract(config):
    """Только извлечь ресурсы с Tilda"""
    try:
        cfg = Config(config)
        setup_logging(cfg.logging.file, cfg.logging.level)
        
        agent = MigrationAgent(cfg)
        agent.extract_only()
        
    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
def deploy(config):
    """Только развернуть на Google Cloud"""
    try:
        cfg = Config(config)
        setup_logging(cfg.logging.file, cfg.logging.level)
        
        agent = MigrationAgent(cfg)
        agent.deploy_only()
        
    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
def validate(config):
    """Проверить конфигурацию и подключения"""
    try:
        cfg = Config(config)
        setup_logging(cfg.logging.file, cfg.logging.level)
        
        agent = MigrationAgent(cfg)
        agent.validate_configuration()
        
    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli() 