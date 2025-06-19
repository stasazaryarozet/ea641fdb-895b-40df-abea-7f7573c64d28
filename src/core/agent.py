"""
Main migration agent class
"""

import time
from pathlib import Path
from typing import Optional
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import load_config
from ..extractors.tilda_extractor import TildaExtractor
from ..processors.content_processor import ContentProcessor
from ..deployers.google_cloud_deployer import GoogleCloudDeployer
# from ..form_handlers.form_handler import FormHandler # Пока не используется
# from ..utils.logger import setup_logging # Пока не используется


class MigrationAgent:
    """
    Оркестрирует процесс миграции сайта с Tilda на Google Cloud.
    """
    
    def __init__(self, config_path: str, dry_run: bool = False):
        self.config = load_config(config_path)
        self.dry_run = dry_run
        self.console = Console()
        
        # Инъекция зависимостей для лучшей тестируемости
        self.extractor = TildaExtractor(self.config.tilda)
        self.processor = ContentProcessor(self.config.processing)
        self.deployer = GoogleCloudDeployer(self.config.google_cloud)
        # self.form_handler = FormHandler(self.config.forms) # Пока не используется
        
        # Migration state
        self.extracted_data = None
        self.processed_data = None
        self.deployment_url = None
        
        logger.info(f"Migration Agent initialized. Dry run: {self.dry_run}")
        
    def run(self):
        """
        Запускает полный цикл миграции: извлечение, обработка, развертывание.
        """
        try:
            logger.info("Starting migration process...")
            
            # Шаг 1: Извлечение
            pages_list = self._extract()
            if not pages_list:
                logger.warning("No pages found to process. Stopping migration.")
                return

            # Шаг 2: Обработка (пока в упрощенном виде)
            # В будущем здесь будет цикл по всем страницам
            page_to_process = self.extractor.get_page_full_export(pages_list[0]['id'])
            processed_html = self._process(page_to_process)
            
            # Шаг 3: Развертывание
            self._deploy(processed_html)

            logger.success("Migration process completed successfully!")

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            raise

    def _extract(self) -> list:
        """Извлекает список страниц с Tilda."""
        logger.info("Step 1: Extracting data from Tilda...")
        pages = self.extractor.get_pages_list()
        logger.info(f"Found {len(pages)} pages.")
        return pages

    def _process(self, page_data: dict) -> str:
        """Обрабатывает HTML-контент страницы."""
        logger.info(f"Step 2: Processing content for page ID: {page_data['id']}...")
        html = self.processor.relativize_links(page_data['html'], self.config.tilda.base_url)
        html = self.processor.remove_tilda_elements(html)
        logger.info("Content processed.")
        return html
        
    def _deploy(self, processed_content: str):
        """Развертывает обработанный контент."""
        logger.info("Step 3: Deploying to Google Cloud...")
        if not self.dry_run:
            self.deployer.create_vm_instance()
            # Здесь будет логика загрузки контента на созданную VM
            logger.info("VM creation initiated. Content deployment logic is pending.")
        else:
            logger.info("[DRY RUN] Skipping actual deployment.")

    def validate_configuration(self):
        """Validate configuration and connections"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Проверка конфигурации...", total=None)
            
            # Validate config
            self.config.validate()
            
            # Test Tilda API connection
            self.extractor.test_connection()
            
            # Test Google Cloud connection
            self.deployer.test_connection()
            
            progress.update(task, description="✅ Конфигурация проверена")
    
    def extract_from_tilda(self):
        """Extract all data from Tilda"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Извлечение данных с Tilda...", total=None)
            
            # Extract pages
            pages = self.extractor.extract_pages()
            progress.update(task, description=f"📄 Извлечено {len(pages)} страниц")
            
            # Extract assets
            assets = self.extractor.extract_assets()
            progress.update(task, description=f"📦 Извлечено {len(assets)} ресурсов")
            
            # Extract forms
            forms = self.extractor.extract_forms()
            progress.update(task, description=f"📝 Извлечено {len(forms)} форм")
            
            return {
                'pages': pages,
                'assets': assets,
                'forms': forms
            }
    
    def process_content(self):
        """Process extracted content"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Обработка контента...", total=None)
            
            # Process pages
            processed_pages = self.processor.process_pages(self.extracted_data['pages'])
            progress.update(task, description="📄 Страницы обработаны")
            
            # Process assets
            processed_assets = self.processor.process_assets(self.extracted_data['assets'])
            progress.update(task, description="📦 Ресурсы обработаны")
            
            # Process forms
            processed_forms = self.processor.process_forms(self.extracted_data['forms'])
            progress.update(task, description="📝 Формы обработаны")
            
            return {
                'pages': processed_pages,
                'assets': processed_assets,
                'forms': processed_forms
            }
    
    def deploy_to_google_cloud(self):
        """Deploy to Google Cloud"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Развертывание на Google Cloud...", total=None)
            
            # New deployment flow
            deployment_url = self.deployer.run_deployment(self.processed_data)
            progress.update(task, description="✅ Развертывание завершено")
            
            return deployment_url
    
    def setup_forms(self):
        """Setup form handling (Now part of deployment)"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Настройка обработки форм...", total=None)
            
            progress.update(task, description="✅ Настройка форм завершена")
    
    def finalize_migration(self):
        """Finalize migration (Now part of deployment)"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Финальная настройка...", total=None)
            
            progress.update(task, description="✅ Финальная настройка завершена")
    
    def extract_only(self):
        """Only extract data from Tilda"""
        self.console.print("[bold blue]📥 Извлечение данных с Tilda[/bold blue]")
        
        try:
            self.validate_configuration()
            self.extracted_data = self.extract_from_tilda()
            
            # Save extracted data
            output_dir = Path("extracted_data")
            output_dir.mkdir(exist_ok=True)
            
            # Save to files
            import json
            with open(output_dir / "pages.json", "w", encoding="utf-8") as f:
                json.dump(self.extracted_data['pages'], f, ensure_ascii=False, indent=2)
            
            with open(output_dir / "assets.json", "w", encoding="utf-8") as f:
                json.dump(self.extracted_data['assets'], f, ensure_ascii=False, indent=2)
            
            with open(output_dir / "forms.json", "w", encoding="utf-8") as f:
                json.dump(self.extracted_data['forms'], f, ensure_ascii=False, indent=2)
            
            self.console.print(f"[green]✅ Данные сохранены в папку {output_dir}[/green]")
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            self.console.print(f"[bold red]❌ Извлечение завершилось с ошибкой: {e}[/bold red]")
            raise
    
    def deploy_only(self):
        """Only deploy to Google Cloud (assumes data is already extracted)"""
        self.console.print("[bold blue]☁️ Развертывание на Google Cloud[/bold blue]")
        
        try:
            # Load extracted data
            import json
            extracted_dir = Path("extracted_data")
            
            if not extracted_dir.exists():
                raise FileNotFoundError("Extracted data not found. Run extract first.")
            
            with open(extracted_dir / "pages.json", "r", encoding="utf-8") as f:
                pages = json.load(f)
            with open(extracted_dir / "assets.json", "r", encoding="utf-8") as f:
                assets = json.load(f)
            with open(extracted_dir / "forms.json", "r", encoding="utf-8") as f:
                forms = json.load(f)
            
            self.extracted_data = {
                'pages': pages,
                'assets': assets,
                'forms': forms
            }
            
            # Process and deploy
            self.processed_data = self.process_content()
            self.deployment_url = self.deploy_to_google_cloud()
            self.setup_forms()
            self.finalize_migration()
            
            self.console.print(f"[green]✅ Развертывание завершено: {self.deployment_url}[/green]")
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            self.console.print(f"[bold red]❌ Развертывание завершилось с ошибкой: {e}[/bold red]")
            raise 