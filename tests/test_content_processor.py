import pytest
from unittest.mock import MagicMock
from src.processors.content_processor import ContentProcessor
from src.core.config import ProcessingConfig
from bs4 import BeautifulSoup
import cssutils
from urllib.parse import urljoin

@pytest.fixture
def processor_config():
    """Provides a mock ProcessingConfig."""
    mock_config = MagicMock(spec=ProcessingConfig)
    mock_config.optimize_images = False
    mock_config.minify_css = False
    mock_config.minify_js = False
    return mock_config

@pytest.fixture
def processor(processor_config):
    """Provides a ContentProcessor instance."""
    return ContentProcessor(config=processor_config)

def test_process_page_basic_assets(processor):
    """Tests that standard assets (img, css, js) are processed correctly."""
    html_content = """
    <html>
    <head>
        <link rel="stylesheet" href="https://example.com/style.css">
        <script src="https://example.com/script.js"></script>
    </head>
    <body>
        <img src="https://example.com/image.png">
    </body>
    </html>
    """
    page = {'html': html_content, 'url': 'https://example.com/page1'}

    processor._process_page(page)
    
    assert "https://example.com/style.css" in processor.asset_mapping
    assert "https://example.com/script.js" in processor.asset_mapping
    assert "https://example.com/image.png" in processor.asset_mapping
    
    mapping = processor.asset_mapping["https://example.com/style.css"]
    assert mapping["type"] == "css"
    assert mapping["local_path"].startswith("assets/")
    assert mapping["local_path"].endswith(".css")

def test_font_url_in_css_is_found(processor, monkeypatch):
    """
    Tests that font URLs referenced inside a CSS file are correctly
    detected, processed, and that the CSS content is updated.
    """
    # 1. Mock the 'requests.get' call to return our fake CSS content
    font_url = 'https://example.com/fonts/myfont.woff2'
    css_content = f"""
    @font-face {{
        font-family: 'MyFont';
        src: url('{font_url}');
    }}
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = css_content.encode('utf-8')
    monkeypatch.setattr("requests.get", MagicMock(return_value=mock_response))

    # 2. Define an initial page that links to this CSS
    css_url = "https://example.com/style.css"
    html_content = f'<link rel="stylesheet" href="{css_url}">'
    page = {'html': html_content, 'url': 'https://example.com/page1'}

    # 3. Process the page, which should identify the CSS file
    processor._process_page(page)
    assert css_url in processor.asset_mapping

    # 4. Now, process the assets. This should trigger the CSS parsing.
    css_asset = {
        'url': css_url,
        'content': css_content.encode('utf-8'),
        'type': 'css'
    }
    processed_asset = processor._process_asset(css_asset)
    processed_css = processed_asset['content'].decode('utf-8')

    # 5. Assert that the font was found and mapped
    assert font_url in processor.asset_mapping
    font_mapping = processor.asset_mapping[font_url]
    assert font_mapping["type"] == "asset"
    
    # 6. Assert that the CSS content was updated with the new local path
    local_font_path = font_mapping["local_path"]
    assert f"url({local_font_path})" in processed_css or f"url('{local_font_path}')" in processed_css or f'url("{local_font_path}")' in processed_css 