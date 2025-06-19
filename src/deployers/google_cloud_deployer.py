#!/usr/bin/env python3
"""
Google Cloud Deployer
Deploys a static site to GCS and a form handler to Cloud Functions using the gcloud CLI.
"""

import os
from pathlib import Path
import subprocess
import zipfile
from loguru import logger
from dotmap import DotMap
from google.oauth2 import service_account
from googleapiclient import discovery

class GoogleCloudDeployer:
    """
    Развертывает ресурсы в Google Cloud с использованием Python SDK.
    """
    
    def __init__(self, config: DotMap):
        self.config = config
        self.project_id = self.config.project_id
        self.region = self.config.region
        self.zone = self.config.zone
        
        try:
            # Аутентификация с использованием файла ключа сервис-аккаунта
            self.credentials = service_account.Credentials.from_service_account_file(
                self.config.credentials_file,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            self.compute = discovery.build('compute', 'v1', credentials=self.credentials)
            logger.info("Google Cloud Deployer initialized successfully.")
        except FileNotFoundError:
            logger.error(f"Credentials file not found at: {self.config.credentials_file}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud client: {e}")
            raise

    def create_vm_instance(self):
        """
        Создает инстанс виртуальной машины в Compute Engine.
        """
        vm_config = self.config.vm
        logger.info(f"Requesting VM instance creation: {vm_config.name} in {self.zone}")

        vm_body = {
            "name": vm_config.name,
            "machineType": f"zones/{self.zone}/machineTypes/{vm_config.machine_type}",
            "disks": [{
                "boot": True,
                "autoDelete": True,
                "initializeParams": {
                    "sourceImage": f"projects/{vm_config.image_project}/global/images/{vm_config.image_family}",
                    "diskSizeGb": str(vm_config.disk_size_gb)
                }
            }],
            "networkInterfaces": [{
                "network": "global/networks/default",
                "accessConfigs": [{
                    "type": "ONE_TO_ONE_NAT",
                    "name": "External NAT"
                }]
            }]
        }

        try:
            request = self.compute.instances().insert(
                project=self.project_id,
                zone=self.zone,
                body=vm_body
            )
            response = request.execute()
            
            logger.info(f"Waiting for VM creation operation to complete...")
            self.compute.zoneOperations().wait(
                project=self.project_id,
                zone=self.zone,
                operation=response['name']
            ).execute()
            
            logger.success(f"✅ VM instance '{vm_config.name}' created successfully.")

        except Exception as e:
            logger.error(f"Failed to create VM instance: {e}")
            raise

    def deploy_static_site(self):
        """Deploys the static site from the 'dist' directory to GCS using gsutil."""
        logger.info(f"🚀 Deploying static site from '{self.dist_path}' to GCS...")
        if not self.dist_path.exists():
            logger.error(f"❌ Distribution directory '{self.dist_path}' not found. Run 'process' first.")
            raise FileNotFoundError(f"Directory not found: {self.dist_path}")

        bucket_uri = f"gs://{self.gcp_config.gcs.bucket_name}"
        
        # Use rsync to efficiently upload files
        logger.info(f"📤 Syncing '{self.dist_path}' with '{bucket_uri}'...")
        self._run_command(['gsutil', '-m', 'rsync', '-r', '-c', str(self.dist_path), bucket_uri])

        # Set the main page for the website
        self._run_command(['gsutil', 'web', 'set', '-m', 'index.html', bucket_uri])
        
        # Make the bucket public
        logger.info(f"Setting public access policy on bucket {self.gcp_config.gcs.bucket_name}...")
        self._run_command(['gsutil', 'iam', 'ch', 'allUsers:objectViewer', bucket_uri])

        logger.info("🎉 Static site deployment successful!")
        logger.info(f"🔗 Site URL: {self.gcs_static_url}")

    def deploy_form_handler_function(self) -> str:
        """Packages, uploads, and deploys the form handler Cloud Function via gcloud."""
        handler_config = self.config.forms.get('google_sheets_handler')
        if not (handler_config and handler_config.enabled):
            logger.info("Form handler deployment is disabled. Skipping.")
            return ""

        logger.info("🚀 Deploying form handler to Cloud Functions...")
        
        project_id = self.gcp_config.project_id
        region = handler_config.region
        function_name = handler_config.function_name
        source_dir = Path("form_handler")

        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory for form handler not found: {source_dir}")

        deploy_command = [
            'gcloud', 'functions', 'deploy', function_name,
            '--project', project_id,
            '--region', region,
            '--runtime', 'python39',
            '--trigger-http',
            '--entry-point', 'handle_form',
            '--source', str(source_dir),
            '--allow-unauthenticated',
            f"--set-env-vars=SPREADSHEET_ID={handler_config.spreadsheet_id},SHEET_NAME={handler_config.sheet_name}"
        ]
        
        self._run_command(deploy_command)
        
        # Get the URL of the deployed function
        url = self._run_command(
            ['gcloud', 'functions', 'describe', function_name, '--project', project_id, '--region', region, '--format=value(httpsTrigger.url)'],
            capture=True
        ).strip()
        
        logger.info(f"✅ Function '{function_name}' deployed successfully.")
        logger.info(f"🔗 URL: {url}")
        
        return url 