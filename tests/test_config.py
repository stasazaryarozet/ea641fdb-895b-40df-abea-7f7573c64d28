import pytest
import yaml
from pathlib import Path
from dotmap import DotMap

# Define the path to the config file at the module level
CONFIG_PATH = Path(__file__).parent.parent / 'config.yaml'

@pytest.fixture(scope="module")
def config() -> DotMap:
    """Loads the main config file and returns it as a DotMap."""
    if not CONFIG_PATH.exists():
        pytest.fail(f"Configuration file not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    return DotMap(config_data)

def test_config_loads_successfully(config):
    """Checks if the config file loads and is a DotMap."""
    assert config is not None
    assert isinstance(config, DotMap)
    assert config.to_dict is not None # Ensure it's not empty

def test_required_top_level_sections(config):
    """Tests that essential top-level sections are present."""
    required_sections = ['tilda', 'google_cloud', 'forms', 'logging', 'processing']
    for section in required_sections:
        assert section in config, f"Missing required section '{section}' in config.yaml"
        assert isinstance(config[section], DotMap), f"Section '{section}' should be a dictionary."

def test_tilda_config_section(config):
    """Validates the 'tilda' section of the config."""
    assert 'base_url' in config.tilda, "Missing 'base_url' in tilda section"
    assert 'output_dir' in config.tilda, "Missing 'output_dir' in tilda section"
    assert isinstance(config.tilda.base_url, str)
    assert config.tilda.base_url.startswith('http'), "Tilda 'base_url' should be a valid URL"

def test_google_cloud_config_section(config):
    """Validates the 'google_cloud' section."""
    gcp = config.google_cloud
    assert 'project_id' in gcp, "Missing 'project_id' in google_cloud section"
    assert 'region' in gcp, "Missing 'region' in google_cloud section"
    assert 'gcs' in gcp, "Missing 'gcs' subsection in google_cloud"
    assert 'bucket_name' in gcp.gcs, "Missing 'bucket_name' in gcs subsection"

def test_forms_config_section(config):
    """Validates the 'forms' and 'google_sheets_handler' sections."""
    forms = config.forms
    assert 'google_sheets_handler' in forms, "Missing 'google_sheets_handler' in forms section"
    handler = forms.google_sheets_handler
    assert 'enabled' in handler, "Missing 'enabled' flag in google_sheets_handler"
    assert isinstance(handler.enabled, bool)
    
    if handler.enabled:
        assert 'region' in handler, "Missing 'region' in google_sheets_handler"
        assert 'function_name' in handler, "Missing 'function_name' in google_sheets_handler"
        assert 'spreadsheet_id' in handler, "Missing 'spreadsheet_id' in google_sheets_handler"
        assert 'sheet_name' in handler, "Missing 'sheet_name' in google_sheets_handler"

def test_logging_config_section(config):
    """Validates the 'logging' section."""
    logging = config.logging
    assert 'level' in logging, "Missing 'level' in logging section"
    assert logging.level in ['DEBUG', 'INFO', 'WARNING', 'ERROR'], "Invalid logging level"

def test_processing_config_section(config):
    """Validates the 'processing' section."""
    processing = config.processing
    assert 'asset_domains' in processing, "Missing 'asset_domains' in processing section"
    assert isinstance(processing.asset_domains, list), "'asset_domains' should be a list"
    assert 'download_assets' in processing, "Missing 'download_assets' in processing section"
    assert isinstance(processing.download_assets, bool) 