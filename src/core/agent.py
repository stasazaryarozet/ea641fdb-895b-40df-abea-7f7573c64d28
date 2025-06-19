"""
Main migration agent class
"""

import time
from pathlib import Path
from typing import Optional
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config
from extractors.tilda_extractor import TildaExtractor
from processors.content_processor import ContentProcessor
from deployers.google_cloud_deployer import GoogleCloudDeployer
from form_handlers.form_handler import FormHandler
from utils.logger import setup_logging


class MigrationAgent:
    """Main agent for Tilda to Google Cloud migration"""
    
    def __init__(self, config: Config, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.console = Console()
        
        # Initialize components
        self.extractor = TildaExtractor(config.tilda)
        self.processor = ContentProcessor(config.processing)
        self.deployer = GoogleCloudDeployer(config, dry_run)
        self.form_handler = FormHandler(config.forms)
        
        # Migration state
        self.extracted_data = None
        self.processed_data = None
        self.deployment_url = None
        
    def run(self):
        """Run complete migration process"""
        self.console.print("[bold blue]🚀 Запуск миграции Tilda → Google Cloud[/bold blue]")
        
        try:
            # Step 1: Validate configuration
            self.console.print("\n[bold]1️⃣ Проверка конфигурации...[/bold]")
            self.validate_configuration()
            
            # Step 2: Extract from Tilda
            self.console.print("\n[bold]2️⃣ Извлечение данных с Tilda...[/bold]")
            self.extracted_data = self.extract_from_tilda()
            
            # Step 3: Process content
            self.console.print("\n[bold]3️⃣ Обработка контента...[/bold]")
            self.processed_data = self.process_content()
            
            # Step 4: Deploy to Google Cloud
            self.console.print("\n[bold]4️⃣ Развертывание на Google Cloud...[/bold]")
            self.deployment_url = self.deploy_to_google_cloud()
            
            # Step 5: Setup forms
            self.console.print("\n[bold]5️⃣ Настройка обработки форм...[/bold]")
            self.setup_forms()
            
            # Step 6: Finalize
            self.console.print("\n[bold]6️⃣ Финальная настройка...[/bold]")
            self.finalize_migration()
            
            self.console.print(f"\n[bold green]✅ Миграция завершена успешно![/bold green]")
            self.console.print(f"[green]🌐 Сайт доступен по адресу: {self.deployment_url}[/green]")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.console.print(f"\n[bold red]❌ Миграция завершилась с ошибкой: {e}[/bold red]")
            raise
    
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
            
            # Create VM
            vm_url = self.deployer.create_vm()
            progress.update(task, description="🖥️ Виртуальная машина создана")
            
            # Upload content
            self.deployer.upload_content(self.processed_data)
            progress.update(task, description="📤 Контент загружен")
            
            # Configure web server
            self.deployer.configure_web_server()
            progress.update(task, description="🌐 Веб-сервер настроен")
            
            # Setup SSL
            self.deployer.setup_ssl()
            progress.update(task, description="🔒 SSL сертификат настроен")
            
            return vm_url
    
    def setup_forms(self):
        """Setup form handling"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Настройка обработки форм...", total=None)
            
            # Deploy form handler
            self.form_handler.deploy_handler()
            progress.update(task, description="📝 Обработчик форм развернут")
            
            # Configure endpoints
            self.form_handler.configure_endpoints(self.processed_data['forms'])
            progress.update(task, description="🔗 Эндпоинты настроены")
    
    def finalize_migration(self):
        """Finalize migration"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Финальная настройка...", total=None)
            
            # Setup monitoring
            if self.config.deployment.monitoring:
                self.deployer.setup_monitoring()
            progress.update(task, description="📊 Мониторинг настроен")
            
            # Setup backups
            if self.config.deployment.auto_backup:
                self.deployer.setup_backups()
            progress.update(task, description="💾 Резервное копирование настроено")
            
            # Health check
            self.deployer.health_check()
            progress.update(task, description="✅ Проверка работоспособности")
    
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