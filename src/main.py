#!/usr/bin/env python3
"""
Tilda to Google Cloud Migration Agent (Simple Static Site Version)
"""

import sys
from pathlib import Path
import json
import requests
import shutil
from typing import Dict
import yaml
from dotmap import DotMap

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import click
from loguru import logger

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
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    cfg = DotMap(config_data)
    setup_logging(level=cfg.logging.level)
    return cfg

def _download_assets_recursively(assets_to_download: Dict, cfg: DotMap, dist_path: Path, processor: ContentProcessor):
    """Downloads assets, searching for new assets within downloaded CSS files."""
    download_queue = set(assets_to_download.keys())
    processed_urls = set()

    while download_queue:
        url_to_download = download_queue.pop()
        if url_to_download in processed_urls:
            continue
        
        processed_urls.add(url_to_download)
        asset_info = assets_to_download.get(url_to_download)
        if not asset_info:
            asset_info = {'local_path': processor._generate_local_path(url_to_download)}

        logger.debug(f"Downloading asset: {url_to_download}")
        try:
            response = requests.get(url_to_download, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()

            asset_path = dist_path / asset_info['local_path']
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            with open(asset_path, 'wb') as f:
                f.write(response.content)

            if 'css' in response.headers.get('Content-Type', '') or asset_info['local_path'].endswith('.css'):
                logger.debug(f"Scanning CSS file for more assets: {asset_info['local_path']}")
                css_content = response.content.decode('utf-8', errors='ignore')
                new_urls = processor.extract_new_urls_from_css(css_content, base_url=url_to_download)
                for new_url in new_urls:
                    if new_url not in processed_urls:
                        download_queue.add(new_url)
                        if new_url not in assets_to_download:
                           assets_to_download[new_url] = {'local_path': processor._generate_local_path(new_url)}

        except requests.RequestException as e:
            logger.warning(f"Could not download asset {url_to_download}: {e}")


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
@click.option('--form-handler-url', default=None, help='URL of the deployed form handler.')
def process(config, form_handler_url):
    """Processes extracted data and prepares it for deployment in `dist/`."""
    try:
        cfg = _load_config_and_logging(config)
        if form_handler_url:
            logger.info(f"Using form handler URL: {form_handler_url}")
        else:
            logger.warning("No form handler URL provided. Forms will not be updated.")

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
                 
        logger.info(f"Downloading assets recursively...")
        _download_assets_recursively(assets_to_download, cfg, dist_path, processor)
        logger.info(f"✅ Assets saved to '{dist_path}'. Processing complete.")
        
    except Exception as e:
        logger.error(f"❌ An error occurred during processing: {e}")
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file.')
def deploy_handler(config):
    """Deploys the form handler to Google Cloud Functions."""
    try:
        cfg = _load_config_and_logging(config)
        logger.info("4️⃣ Deploying form handler to Google Cloud Functions...")
        deployer = GoogleCloudDeployer(cfg)
        url = deployer.deploy_form_handler_function()
        if url:
             logger.info(f"✅ Form handler deployment complete. URL: {url}")
        else:
             logger.info("✅ Form handler deployment skipped as per configuration.")
    except Exception as e:
        logger.error(f"❌ An error occurred during form handler deployment: {e}")
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file.')
def deploy_static(config):
    """Deploys the processed files from `dist/` to Google Cloud Storage."""
    try:
        cfg = _load_config_and_logging(config)
        logger.info("5️⃣ Deploying to Google Cloud Storage...")
        deployer = GoogleCloudDeployer(cfg)
        deployer.deploy_static_site()
        logger.info("✅ Deployment to GCS complete.")
    except Exception as e:
        logger.error(f"❌ An error occurred during deployment: {e}")
        sys.exit(1)


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file.')
def migrate(config):
    """Run the full migration process: Extract -> Deploy Handler -> Process -> Deploy Static."""
    ctx = click.get_current_context()
    try:
        # 1. Extract
        logger.info("\n--- Running Step 1: Extract ---")
        ctx.invoke(extract, config=config)

        # 2. Deploy Handler
        logger.info("\n--- Running Step 2: Deploy Form Handler ---")
        cfg = _load_config_and_logging(config)
        deployer = GoogleCloudDeployer(cfg)
        form_url = deployer.deploy_form_handler_function()

        # 3. Process
        logger.info("\n--- Running Step 3: Process ---")
        ctx.invoke(process, config=config, form_handler_url=form_url)

        # 4. Deploy Static
        logger.info("\n--- Running Step 4: Deploy Static Site ---")
        ctx.invoke(deploy_static, config=config)

        logger.info("\n🎉 Full migration process finished successfully!")
    except Exception as e:
        logger.error(f"❌ The migration process failed. Please review the logs. Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli.add_command(migrate)
    cli() 