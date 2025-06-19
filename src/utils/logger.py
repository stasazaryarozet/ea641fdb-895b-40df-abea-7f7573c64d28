"""
Logging utilities for Tilda migration agent
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(log_file: str = "logs/migration.log", level: str = "INFO"):
    """Setup logging configuration"""
    
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # Add file handler
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    logger.info(f"Logging configured - level: {level}, file: {log_file}")


def get_logger(name: str = None):
    """Get logger instance"""
    return logger.bind(name=name) if name else logger 