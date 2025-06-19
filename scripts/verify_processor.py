import sys
from pathlib import Path
from loguru import logger
import json

# Add project root to path to allow imports from src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.extractors.tilda_extractor import TildaExtractor
from src.processors.content_processor import ContentProcessor
from src.utils.logger import setup_logging

def test_processor():
    """
    This script runs the extraction and processing steps of the migration
    and saves the output locally for verification before deployment.
    """
    setup_logging(level="DEBUG")
    logger.info("🚀 Starting content processor test...")

    try:
        # 1. Load Config
        logger.info("1️⃣ Loading configuration...")
        config = Config(config_path="config.yaml")
        logger.info("✅ Configuration loaded.")

        # 2. Extract Data
        logger.info("\n2️⃣ Extracting data from Tilda...")
        extractor = TildaExtractor(config.tilda)
        pages = extractor.extract_pages()
        if not pages:
            logger.error("❌ No pages were extracted. Halting test.")
            return
        logger.info(f"✅ Extracted {len(pages)} page(s).")

        # 3. Process Content
        logger.info("\n3️⃣ Processing content...")
        processor = ContentProcessor(config.processing)
        processed_pages = processor.process_pages(pages)
        asset_mapping = processor.get_asset_mapping()
        logger.info("✅ Content processed.")

        # 4. Save artifacts for inspection
        logger.info("\n4️⃣ Saving artifacts for inspection...")
        output_dir = project_root / "extracted_data" / "test_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save processed HTML
        if processed_pages:
            processed_html_path = output_dir / "processed_page.html"
            processed_html_path.write_text(processed_pages[0]['html'], encoding='utf-8')
            logger.info(f"📄 Saved processed HTML to: {processed_html_path}")

        # Save asset mapping
        asset_mapping_path = output_dir / "asset_mapping.json"
        with asset_mapping_path.open('w', encoding='utf-8') as f:
            json.dump(asset_mapping, f, indent=4, ensure_ascii=False)
        logger.info(f"🗺️ Saved asset mapping to: {asset_mapping_path}")
        
        logger.info("\n✅ Test finished successfully. Please inspect the files in `extracted_data/test_output`.")

    except Exception as e:
        logger.error(f"❌ Test failed with an error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_processor() 