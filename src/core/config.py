"""
Configuration management for Tilda migration agent
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TildaConfig:
    api_key: str
    secret_key: str
    project_id: str
    base_url: str
    
    @property
    def use_api(self) -> bool:
        """Check if API keys are provided for API-based extraction"""
        return bool(self.api_key and self.secret_key and self.project_id)


@dataclass
class GoogleCloudConfig:
    project_id: str
    region: str
    zone: str
    credentials_file: str
    vm: Dict[str, Any]
    storage: Dict[str, Any]
    dns: Dict[str, Any]


@dataclass
class FormsConfig:
    email_service: str
    sendgrid_api_key: Optional[str]
    smtp: Dict[str, Any]
    endpoints: Dict[str, str]


@dataclass
class LoggingConfig:
    level: str
    file: str
    max_size: str
    rotation: str


@dataclass
class ProcessingConfig:
    download_images: bool
    optimize_images: bool
    minify_css: bool
    minify_js: bool
    preserve_original_structure: bool


@dataclass
class DeploymentConfig:
    web_server: str
    ssl_certificate: str
    auto_backup: bool
    monitoring: bool


class Config:
    """Main configuration class"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Parse configuration sections
        self.tilda = TildaConfig(**config_data.get('tilda', {}))
        self.google_cloud = GoogleCloudConfig(**config_data.get('google_cloud', {}))
        self.forms = FormsConfig(**config_data.get('forms', {}))
        self.logging = LoggingConfig(**config_data.get('logging', {}))
        self.processing = ProcessingConfig(**config_data.get('processing', {}))
        self.deployment = DeploymentConfig(**config_data.get('deployment', {}))
        
        # Store raw config for backward compatibility
        self.raw = config_data
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        # Validate Tilda configuration
        if not self.tilda.base_url:
            errors.append("Tilda base URL is required")
        
        # Only require API keys if using API-based extraction
        if self.tilda.use_api:
            if not self.tilda.api_key:
                errors.append("Tilda API key is required for API-based extraction")
            if not self.tilda.secret_key:
                errors.append("Tilda secret key is required for API-based extraction")
            if not self.tilda.project_id:
                errors.append("Tilda project ID is required for API-based extraction")
        
        # Validate Google Cloud configuration
        if not self.google_cloud.project_id:
            errors.append("Google Cloud project ID is required")
        if not self.google_cloud.credentials_file:
            errors.append("Google Cloud credentials file is required")
        
        # Validate credentials file exists
        if self.google_cloud.credentials_file and not Path(self.google_cloud.credentials_file).exists():
            errors.append(f"Google Cloud credentials file not found: {self.google_cloud.credentials_file}")
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
        
        return True
    
    def get_environment_vars(self) -> Dict[str, str]:
        """Get environment variables for sensitive data"""
        env_vars = {}
        
        # Check for environment variables for sensitive data
        if os.getenv('TILDA_API_KEY'):
            self.tilda.api_key = os.getenv('TILDA_API_KEY')
        if os.getenv('TILDA_SECRET_KEY'):
            self.tilda.secret_key = os.getenv('TILDA_SECRET_KEY')
        if os.getenv('GOOGLE_CLOUD_PROJECT'):
            self.google_cloud.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            self.google_cloud.credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if os.getenv('SENDGRID_API_KEY'):
            self.forms.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        
        return env_vars 