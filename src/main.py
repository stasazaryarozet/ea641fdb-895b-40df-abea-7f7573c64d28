#!/usr/bin/env python3
"""
Tilda to Google Cloud Migration Agent (Simple Static Site Version)
"""

import sys
from pathlib import Path
import json
import requests
import shutil

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import click
from loguru import logger

from src.core.config import Config
from src.utils.logger import setup_logging
from src.extractors.tilda_extractor import TildaExtractor
from src.processors.content_processor import ContentProcessor
from src.deployers.google_cloud_deployer import GoogleCloudDeployer


@click.group()
def cli():
    """A simple tool to migrate a Tilda site to a static hosting on GCS."""
    pass


# --- Helper Functions for Commands ---

def _load_config_and_logging(config_path: str):
    logger.info("1️⃣ Loading configuration...")
    cfg = Config(config_path)
    setup_logging(level=cfg.logging.level)
    return cfg

def _get_form_url(cfg: Config):
    form_handler_url = getattr(cfg.forms, 'form_handler_url', None)
    if not form_handler_url:
        logger.warning("⚠️ `forms.form_handler_url` is not set in your config file. Forms will not work.")
    else:
        logger.info(f"✅ Form handler URL is set to: {form_handler_url}")
    return form_handler_url

# --- Individual Commands ---

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file.')
def extract(config):
    """Extracts data from Tilda and saves it locally."""
    try:
        cfg = _load_config_and_logging(config)
        logger.info("2️⃣ Extracting data from Tilda...")
        extractor = TildaExtractor(cfg.tilda)
        extractor.extract_pages()
        extractor.extract_forms()
        logger.info(f"✅ Raw data saved to '{extractor.output_path}'")
    except Exception as e:
        logger.error(f"❌ An error occurred during extraction: {e}")
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file.')
def process(config):
    """Processes extracted data and prepares it for deployment in `dist/`."""
    try:
        cfg = _load_config_and_logging(config)
        form_handler_url = _get_form_url(cfg)
        
        logger.info("3️⃣ Processing content...")
        
        output_dir = Path(getattr(cfg.tilda, 'output_dir', 'extracted_data'))
        pages_path = output_dir / 'pages.json'
        if not pages_path.exists():
            logger.error(f"❌ Pages data not found at '{pages_path}'. Please run 'extract' first.")
            sys.exit(1)
            
        with open(pages_path, 'r') as f:
            pages = json.load(f)
            
        processor = ContentProcessor(cfg.processing, form_handler_url)
        processed_pages = processor.process_pages(pages)
        assets_to_download = processor.get_asset_mapping()
        
        dist_path = Path("dist")
        if dist_path.exists():
            shutil.rmtree(dist_path)
        dist_path.mkdir(exist_ok=True)
        
        for page in processed_pages:
             page_path = dist_path / page['filename']
             page_path.parent.mkdir(parents=True, exist_ok=True)
             with open(page_path, 'w', encoding='utf-8') as f:
                 f.write(page['html'])
        logger.info(f"✅ Processed pages saved to '{dist_path}'")
                 
        logger.info(f"Downloading {len(assets_to_download)} assets...")
        for original_url, asset_info in assets_to_download.items():
            try:
                # Ensure the URL is absolute
                if not original_url.startswith(('http:', 'https:')):
                    base_url = getattr(cfg.tilda, 'base_url', '')
                    full_url = f"{base_url.rstrip('/')}/{original_url.lstrip('/')}"
                else:
                    full_url = original_url
                    
                response = requests.get(full_url, timeout=15)
                response.raise_for_status()
                asset_path = dist_path / asset_info['local_path']
                asset_path.parent.mkdir(parents=True, exist_ok=True)
                with open(asset_path, 'wb') as f:
                    f.write(response.content)
            except requests.RequestException as e:
                logger.warning(f"Could not download asset {full_url}: {e}")
        logger.info(f"✅ Assets saved to '{dist_path}'. Processing complete.")

    except Exception as e:
        logger.error(f"❌ An error occurred during processing: {e}")
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file.')
def deploy(config):
    """Deploys the processed files from `dist/` to Google Cloud Storage."""
    try:
        cfg = _load_config_and_logging(config)
        logger.info("4️⃣ Deploying to Google Cloud Storage...")
        deployer = GoogleCloudDeployer(cfg)
        deployer.deploy_static_site()
        logger.info("✅ Deployment to GCS complete.")
    except Exception as e:
        logger.error(f"❌ An error occurred during deployment: {e}")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file.')
def migrate(config):
    """Run the full migration process: Extract -> Process -> Deploy."""
    try:
        ctx = click.Context(migrate)
        ctx.invoke(extract, config=config)
        ctx.invoke(process, config=config)
        ctx.invoke(deploy, config=config)
        logger.info("\n🎉 Full migration process finished successfully!")
    except Exception as e:
        # The individual commands already log their errors, so this is a final catch-all
        logger.error(f"❌ The migration process failed at some stage. Please review the logs.")
        sys.exit(1)


if __name__ == '__main__':
    cli()