#!/usr/bin/env python3
"""
Google Cloud Deployer (Static Only)
Deploys a static site to Google Cloud Storage.
"""
import os
from pathlib import Path
from typing import Dict, Any, List

import google.api_core.exceptions as google_exceptions
from google.cloud import storage
from loguru import logger

from src.core.config import Config


class GoogleCloudDeployer:
    """Deploys static files to Google Cloud Storage."""
    
    def __init__(self, config: Config, dry_run: bool = False):
        self.config = config
        self.gcp_config = config.google_cloud
        self.dry_run = dry_run
        self.dist_path = Path(getattr(self.gcp_config, "dist_dir", "dist"))
        self.storage_client = None
        self.gcs_static_url = ""
        
        if not self.dry_run:
            self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Google Cloud clients using credentials."""
        credentials_file = getattr(self.gcp_config, 'credentials_file', None)
        if not credentials_file or not Path(credentials_file).exists():
            logger.error(f"❌ Credentials file not found at '{credentials_file}'.")
            raise FileNotFoundError(f"Credentials file not found at '{credentials_file}'")
        
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_file
        
        try:
            self.storage_client = storage.Client()
            logger.info("✅ Google Cloud client for GCS initialized")
        except Exception as e:
            logger.error(f"❌ GCS client connection failed: {e}")
            raise
    
    def deploy_static_site(self):
        """Deploys the static site from the 'dist' directory to GCS."""
        logger.info(f"🚀 Deploying static site from '{self.dist_path}' to GCS...")
        if not self.dist_path.exists():
            logger.error(f"❌ Distribution directory '{self.dist_path}' not found. Run 'process' first.")
            raise FileNotFoundError(f"Directory not found: {self.dist_path}")

        try:
            self._upload_files_to_gcs()
            logger.info("🎉 Static site deployment successful!")
            logger.info(f"🔗 Site URL: {self.gcs_static_url}")
        except Exception as e:
            logger.error(f"❌ Static site deployment failed: {e}")
            raise
    
    def _upload_files_to_gcs(self):
        """Uploads all files from the dist directory to GCS and makes them public."""
        bucket_name = self.gcp_config.gcs['bucket_name']
        logger.info(f"📤 Uploading all files from '{self.dist_path}' to GCS bucket: {bucket_name}")
        self.gcs_static_url = f"https://storage.googleapis.com/{bucket_name}/index.html"

        try:
            bucket = self.storage_client.get_bucket(bucket_name)
        except google_exceptions.NotFound:
            logger.info(f"Bucket {bucket_name} not found. Creating...")
            bucket = self.storage_client.create_bucket(bucket_name, location=self.gcp_config.region)
            logger.info(f"Bucket {bucket_name} created.")

        for file_path in self.dist_path.rglob('*'):
            if file_path.is_file():
                destination_blob_name = str(file_path.relative_to(self.dist_path))
                blob = bucket.blob(destination_blob_name)
                
                content_type = "application/octet-stream"
                if destination_blob_name.endswith(".html"):
                    content_type = "text/html"
                elif destination_blob_name.endswith(".css"):
                    content_type = "text/css"
                elif destination_blob_name.endswith(".js"):
                    content_type = "application/javascript"

                blob.upload_from_filename(str(file_path), content_type=content_type)
        
        logger.info(f"Setting public access policy on bucket {bucket_name}...")
        bucket.iam_configuration.uniform_bucket_level_access_enabled = False
        bucket.patch()
        policy = bucket.get_iam_policy(requested_policy_version=3)
        
        # Check if the binding already exists
        viewer_binding = {"role": "roles/storage.objectViewer", "members": {"allUsers"}}
        if viewer_binding not in policy.bindings:
            policy.bindings.append(viewer_binding)
            bucket.set_iam_policy(policy)
            logger.info("✅ Public access policy set.")
        else:
            logger.info("✅ Public access policy already in place.")
        
        logger.info(f"✅ All files uploaded to gs://{bucket_name}.") 