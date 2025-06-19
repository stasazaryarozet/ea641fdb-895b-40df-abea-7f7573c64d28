#!/usr/bin/env python3
"""
Setup script for Tilda to Google Cloud Migration Agent
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text().splitlines()

setup(
    name="tilda-migration-agent",
    version="1.0.0",
    description="Автономный ИИ-агент для переноса сайтов с Tilda на Google Cloud",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Tilda Migration Team",
    author_email="support@example.com",
    url="https://github.com/your-org/tilda-migration-agent",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "tilda-migrate=src.main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="tilda migration google cloud automation",
    project_urls={
        "Bug Reports": "https://github.com/your-org/tilda-migration-agent/issues",
        "Source": "https://github.com/your-org/tilda-migration-agent",
        "Documentation": "https://github.com/your-org/tilda-migration-agent/docs",
    },
) 