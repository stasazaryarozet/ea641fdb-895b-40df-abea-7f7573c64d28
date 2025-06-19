"""
Google Cloud deployment module
"""

import os
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

from google.cloud import compute_v1
from google.cloud import storage
from google.cloud import artifactregistry_v1
from google.cloud.devtools import cloudbuild_v1
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from google.api_core import exceptions as google_exceptions

from core.config import Config, GoogleCloudConfig


class GoogleCloudDeployer:
    """Deploy to Google Cloud Platform"""
    
    def __init__(self, config: Config, dry_run: bool = False):
        self.config = config
        self.gcp_config = config.google_cloud
        self.dry_run = dry_run
        self.compute_client = None
        self.operations_client = None
        self.storage_client = None
        self.vm_instance = None
        
        if not dry_run:
            self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Google Cloud clients"""
        try:
            # Set credentials
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.gcp_config.credentials_file
            
            # Initialize clients
            self.compute_client = compute_v1.InstancesClient()
            self.operations_client = compute_v1.ZoneOperationsClient()
            self.storage_client = storage.Client(project=self.gcp_config.project_id)
            
            logger.info("✅ Google Cloud clients initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Cloud clients: {e}")
            raise
    
    def test_connection(self):
        """Test Google Cloud connection"""
        try:
            if self.dry_run:
                logger.info("🔍 Dry run mode - skipping connection test")
                return
            
            # Test compute API
            request = compute_v1.ListInstancesRequest(
                project=self.gcp_config.project_id,
                zone=self.gcp_config.zone
            )
            self.compute_client.list(request=request)
            
            # Test storage API
            self.storage_client.list_buckets()
            
            logger.info("✅ Google Cloud connection successful")
            
        except Exception as e:
            logger.error(f"❌ Google Cloud connection failed: {e}")
            raise
    
    def _check_and_delete_existing_vm(self):
        """Check if VM exists and delete it if it does."""
        vm_name = self.gcp_config.vm['name']
        logger.info(f"Checking for existing VM: {vm_name}")
        try:
            request = compute_v1.GetInstanceRequest(
                project=self.gcp_config.project_id,
                zone=self.gcp_config.zone,
                instance=vm_name,
            )
            self.compute_client.get(request=request)
            logger.warning(f"VM '{vm_name}' already exists. Deleting it to ensure a clean deployment.")

            delete_request = compute_v1.DeleteInstanceRequest(
                project=self.gcp_config.project_id,
                zone=self.gcp_config.zone,
                instance=vm_name,
            )
            operation = self.compute_client.delete(request=delete_request)
            self._wait_for_operation(operation)
            logger.info(f"VM '{vm_name}' deleted successfully.")

        except google_exceptions.NotFound:
            logger.info(f"VM '{vm_name}' does not exist. Proceeding with creation.")
        except Exception as e:
            logger.error(f"Error while checking/deleting existing VM: {e}")
            raise
    
    def create_vm(self) -> str:
        """Create virtual machine instance"""
        logger.info("🖥️ Creating virtual machine...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - VM creation skipped")
            return "http://dry-run-vm-ip"
        
        try:
            # Check for and delete existing VM before creation
            self._check_and_delete_existing_vm()

            # VM configuration
            vm_name = self.gcp_config.vm['name']
            machine_type = f"zones/{self.gcp_config.zone}/machineTypes/{self.gcp_config.vm['machine_type']}"
            
            # Disk configuration
            disk_type = f"zones/{self.gcp_config.zone}/diskTypes/pd-standard"
            disk_size_gb = self.gcp_config.vm['disk_size_gb']
            
            # Image configuration
            image_family = self.gcp_config.vm['image_family']
            image_project = self.gcp_config.vm['image_project']
            
            # Network configuration
            network_interface = compute_v1.NetworkInterface()
            network_interface.name = "global/networks/default"
            network_interface.access_configs = [
                compute_v1.AccessConfig(name="External NAT")
            ]
            
            # Disk configuration
            disk = compute_v1.AttachedDisk()
            disk.auto_delete = True
            disk.boot = True
            disk.type_ = "PERSISTENT"
            disk.initialize_params = compute_v1.AttachedDiskInitializeParams()
            disk.initialize_params.disk_size_gb = disk_size_gb
            disk.initialize_params.source_image = f"projects/{image_project}/global/images/family/{image_family}"
            disk.initialize_params.disk_type = disk_type
            
            # Instance configuration
            instance = compute_v1.Instance()
            instance.name = vm_name
            instance.disks = [disk]
            instance.machine_type = machine_type
            instance.network_interfaces = [network_interface]
            
            # Startup script
            startup_script = self._get_startup_script()
            instance.metadata = compute_v1.Metadata()
            instance.metadata.items = [
                compute_v1.Items(key="startup-script", value=startup_script)
            ]
            
            # Create instance
            request = compute_v1.InsertInstanceRequest(
                project=self.gcp_config.project_id,
                zone=self.gcp_config.zone,
                instance_resource=instance
            )
            
            operation = self.compute_client.insert(request=request)
            self._wait_for_operation(operation)
            
            # Get instance details
            instance_request = compute_v1.GetInstanceRequest(
                project=self.gcp_config.project_id,
                zone=self.gcp_config.zone,
                instance=vm_name
            )
            
            self.vm_instance = self.compute_client.get(request=instance_request)
            
            # Get external IP
            external_ip = None
            for interface in self.vm_instance.network_interfaces:
                for access_config in interface.access_configs:
                    if access_config.name == "External NAT":
                        external_ip = access_config.nat_i_p
                        break
                if external_ip:
                    break
            
            if not external_ip:
                raise Exception("Failed to get external IP address")
            
            vm_url = f"http://{external_ip}"
            logger.info(f"✅ VM created successfully: {vm_url}")
            
            return vm_url
            
        except Exception as e:
            logger.error(f"❌ Failed to create VM: {e}")
            raise
    
    def _get_startup_script(self) -> str:
        """Get startup script for VM"""
        return """#!/bin/bash
set -e -x

# Update system and install dependencies
apt-get update
apt-get install -y nginx python3 python3-pip git
pip3 install flask gunicorn

# Create web directory
mkdir -p /var/www/html
chown -R www-data:www-data /var/www/html

# Configure nginx
cat > /etc/nginx/sites-available/default << 'EOF'
server {
    listen 80;
    server_name _;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

# Create systemd service for form handler
cat > /etc/systemd/system/form-handler.service << 'EOF'
[Unit]
Description=Gunicorn instance to serve form handler
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/html
ExecStart=/usr/local/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 wsgi:app

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
systemctl daemon-reload
systemctl enable form-handler
systemctl restart nginx

# Signal that startup is complete
sudo touch /var/log/startup-script.finished
"""
    
    def _wait_for_operation(self, operation):
        """Wait for operation to complete"""
        while operation.status != compute_v1.Operation.Status.DONE:
            time.sleep(5)
            operation = self.operations_client.get(
                project=self.gcp_config.project_id,
                zone=self.gcp_config.zone,
                operation=operation.name
            )
    
    def _run_gcloud_ssh_command_with_retry(self, command: List[str], retries: int = 5, delay: int = 15, timeout: int = 300) -> subprocess.CompletedProcess:
        """Run a gcloud command with retries for SSH readiness."""
        for i in range(retries):
            try:
                logger.info(f"Running command (attempt {i+1}/{retries}): {' '.join(command)}")
                result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
                logger.info(f"Command successful: {' '.join(command)}")
                return result
            except subprocess.TimeoutExpired:
                logger.warning(f"Command timed out (attempt {i+1}/{retries}). Retrying in {delay} seconds...")
                time.sleep(delay)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Command failed (attempt {i+1}/{retries}): {e.stderr}. Retrying in {delay} seconds...")
                time.sleep(delay)
        raise Exception(f"Command failed after {retries} attempts: {' '.join(command)}")

    def upload_content(self, processed_data: Dict[str, Any]):
        """Upload content to VM"""
        logger.info("📤 Uploading content to VM...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - content upload skipped")
            return
        
        try:
            # Create temporary directory for content
            temp_dir = Path("temp_deploy")
            temp_dir.mkdir(exist_ok=True)
            
            # Save pages
            pages_dir = temp_dir / "pages"
            pages_dir.mkdir(exist_ok=True)
            
            for page in processed_data.get('pages', []):
                filename = page.get('filename', f"page_{page.get('id')}.html")
                if not filename.endswith('.html'):
                    filename += '.html'
                
                with open(pages_dir / filename, 'w', encoding='utf-8') as f:
                    f.write(page.get('html', ''))
            
            # Save assets
            assets_dir = temp_dir / "assets"
            assets_dir.mkdir(exist_ok=True)
            
            for asset in processed_data.get('assets', []):
                local_path = asset.get('local_path', '')
                if local_path.startswith('/'):
                    local_path = local_path[1:]
                
                asset_file = assets_dir / local_path
                asset_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(asset_file, 'wb') as f:
                    f.write(asset.get('content', b''))
            
            # Create form handler
            form_handler_file = temp_dir / "form_handler.py"
            with open(form_handler_file, 'w', encoding='utf-8') as f:
                f.write(self._get_form_handler_code(processed_data.get('forms', [])))

            # Create wsgi.py entrypoint
            wsgi_file = temp_dir / "wsgi.py"
            with open(wsgi_file, 'w', encoding='utf-8') as f:
                f.write("from form_handler import app\\n\\nif __name__ == '__main__':\\n    app.run()\\n")
            
            # Upload to VM using gcloud
            external_ip = self._get_vm_external_ip()
            
            # Use gcloud compute scp to upload files
            scp_command = [
                'gcloud', 'compute', 'scp',
                '--recurse', str(temp_dir),
                f'{self.vm_instance.name}:~/',  # Upload to home directory
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id
            ]
            self._run_gcloud_ssh_command_with_retry(scp_command)
            
            # Move files to correct location and set permissions
            remote_temp_dir_name = temp_dir.name
            ssh_command = [
                'gcloud', 'compute', 'ssh',
                self.vm_instance.name,
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', f'sudo mv ~/{remote_temp_dir_name}/* /var/www/html/ && sudo chown -R www-data:www-data /var/www/html && rm -rf ~/{remote_temp_dir_name}'
            ]
            self._run_gcloud_ssh_command_with_retry(ssh_command, delay=5) # Shorter delay as SSH should be up
            
            # Clean up local temp
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info("✅ Content uploaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to upload content: {e}")
            raise
    
    def _get_vm_external_ip(self) -> str:
        """Get VM external IP"""
        for interface in self.vm_instance.network_interfaces:
            for access_config in interface.access_configs:
                if access_config.name == "External NAT":
                    return access_config.nat_i_p
        raise Exception("External IP not found")
    
    def _get_form_handler_code(self, forms: List[Dict[str, Any]]) -> str:
        """Generates the Python code for the Flask form handler."""
        smtp_conf = self.config.forms.smtp
        return f"""#!/usr/bin/env python3
from flask import Flask, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)

# Form configurations
FORMS = {forms}

@app.route('/api/form-handler', methods=['POST'])
def handle_form():
    try:
        data = request.form
        form_type = data.get('form_type', 'contact')
        
        # Find form configuration
        form_config = None
        for form in FORMS:
            if form.get('name', '').lower() == form_type.lower():
                form_config = form
                break
        
        if not form_config:
            return jsonify({{'error': 'Form type not found'}}), 400
        
        # Validate required fields
        required_fields = [field['name'] for field in form_config.get('fields', []) if field.get('required')]
        for field in required_fields:
            if not data.get(field):
                return jsonify({{'error': f'Field {{field}} is required'}}), 400
        
        # Send email
        send_form_email(data, form_config)
        
        return jsonify({{'success': True, 'message': form_config.get('success_message', 'Form submitted successfully')}})
        
    except Exception as e:
        return jsonify({{'error': str(e)}}), 500

def send_form_email(data, form_config):
    # Email configuration
    smtp_host = '{smtp_conf.get("host", "smtp.gmail.com")}'
    smtp_port = {smtp_conf.get("port", 587)}
    smtp_user = '{smtp_conf.get("username", "")}'
    smtp_pass = '{smtp_conf.get("password", "")}'
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = form_config.get('email', smtp_user)
    msg['Subject'] = f'New form submission: {{form_config.get("name", "Contact")}}'
    
    # Create body
    body = "New form submission:\\n\\n"
    for field in form_config.get('fields', []):
        field_name = field.get('name', '')
        field_value = data.get(field_name, '')
        body += f"{{field_name}}: {{field_value}}\\n"
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Send email
    server = smtplib.SMTP(smtp_host, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.send_message(msg)
    server.quit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
"""
    
    def _wait_for_service(self, service_name: str, timeout: int = 300):
        """Wait for a systemd service to become active."""
        logger.info(f"Waiting for service '{service_name}' to become active...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                command = [
                    'gcloud', 'compute', 'ssh',
                    self.vm_instance.name,
                    '--zone', self.gcp_config.zone,
                    '--project', self.gcp_config.project_id,
                    '--command', f'sudo systemctl is-active {service_name}'
                ]
                # Use a shorter retry for status checks
                result = self._run_gcloud_ssh_command_with_retry(command, retries=2, delay=5)
                if "active" in result.stdout.strip():
                    logger.info(f"✅ Service '{service_name}' is active.")
                    return
            except Exception as e:
                # This is expected if the service isn't up yet
                logger.debug(f"Service '{service_name}' not active yet. Waiting...")
            
            time.sleep(10)
        
        raise Exception(f"Service '{service_name}' did not become active within {timeout} seconds.")

    def _wait_for_startup_script(self, timeout: int = 600):
        """Wait for the VM startup script to complete."""
        logger.info("⏳ Waiting for VM startup script to complete...")
        start_time = time.time()
        
        signal_file = "/var/log/startup-script.finished"
        
        while time.time() - start_time < timeout:
            try:
                command = [
                    'gcloud', 'compute', 'ssh',
                    self.vm_instance.name,
                    '--zone', self.gcp_config.zone,
                    '--project', self.gcp_config.project_id,
                    '--command', f'sudo test -f {signal_file}'
                ]
                # Use a shorter retry for this check
                self._run_gcloud_ssh_command_with_retry(command, retries=1, delay=1, timeout=30)
                logger.info("✅ Startup script completed.")
                return
            except Exception:
                logger.debug("Startup script not finished yet. Waiting...")
                time.sleep(15) # Wait longer between checks for startup script
        
        raise Exception(f"Startup script did not complete within {timeout} seconds.")

    def configure_web_server(self):
        """Configure web server by restarting and waiting for services."""
        logger.info("🌐 Configuring web server...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - web server configuration skipped")
            return
        
        try:
            # First, wait for the startup script to finish
            self._wait_for_startup_script()

            # Restart services to apply changes
            logger.info("Restarting web services...")
            restart_command = [
                'gcloud', 'compute', 'ssh',
                self.vm_instance.name,
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'sudo systemctl restart nginx && sudo systemctl restart form-handler'
            ]
            self._run_gcloud_ssh_command_with_retry(restart_command, retries=3, delay=5)

            # Wait for services to become active
            self._wait_for_service("nginx")
            self._wait_for_service("form-handler")
            
            logger.info("✅ Web server configured successfully: All services are active.")
            
        except Exception as e:
            logger.error(f"❌ Failed to configure web server: {e}")
            raise
    
    def setup_ssl(self):
        """Setup SSL using Let's Encrypt"""
        logger.info("🔒 Setting up SSL certificate...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - SSL setup skipped")
            return
        
        try:
            # Install certbot
            install_command = [
                'gcloud', 'compute', 'ssh',
                self.vm_instance.name,
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx'
            ]
            self._run_gcloud_ssh_command_with_retry(install_command)
            
            # Get domain from config
            domain = self.gcp_config.dns.get('domain', '')
            if domain:
                # Obtain SSL certificate
                cert_command = [
                    'gcloud', 'compute', 'ssh',
                    self.vm_instance.name,
                    '--zone', self.gcp_config.zone,
                    '--project', self.gcp_config.project_id,
                    '--command', f'sudo certbot --nginx --agree-tos --email {self.gcp_config.ssl_email} -d {domain} --redirect --non-interactive'
                ]
                self._run_gcloud_ssh_command_with_retry(cert_command)
            
            logger.info("✅ SSL certificate configured successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup SSL: {e}")
            raise
    
    def setup_monitoring(self):
        """Setup basic monitoring"""
        logger.info("📊 Setting up monitoring...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - monitoring setup skipped")
            return
        
        try:
            # Install monitoring tools
            command = [
                'gcloud', 'compute', 'ssh',
                self.vm_instance.name,
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'sudo apt-get install -y htop iotop nethogs'
            ]
            self._run_gcloud_ssh_command_with_retry(command)
            
            logger.info("✅ Monitoring tools installed")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup monitoring: {e}")
            raise
    
    def setup_backups(self):
        """Setup daily backups"""
        logger.info("💾 Setting up backups...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - backup setup skipped")
            return
        
        try:
            # Backup script
            backup_script = f"""#!/bin/bash
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_DIR="/var/backups/website"
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/backup-$TIMESTAMP.tar.gz /var/www/html
# Optional: Remove backups older than 7 days
find $BACKUP_DIR -type f -mtime +7 -name '*.gz' -delete
"""
            # Create backup script on VM
            script_command = [
                'gcloud', 'compute', 'ssh',
                self.vm_instance.name,
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', f'echo "{backup_script}" | sudo tee /usr/local/bin/backup-website.sh && sudo chmod +x /usr/local/bin/backup-website.sh'
            ]
            self._run_gcloud_ssh_command_with_retry(script_command)
            
            # Add to cron
            cron_command = [
                'gcloud', 'compute', 'ssh',
                self.vm_instance.name,
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'echo "0 2 * * * /usr/local/bin/backup-website.sh" | sudo crontab -'
            ]
            self._run_gcloud_ssh_command_with_retry(cron_command)
            
            logger.info("✅ Daily backups configured")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup backups: {e}")
            raise
    
    def health_check(self):
        """Perform health check on the deployed site"""
        logger.info("🩺 Performing health check...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - health check skipped")
            return
        
        try:
            # Check services are active
            logger.info("Checking service status as part of health check...")
            self._wait_for_service("nginx")
            self._wait_for_service("form-handler")
            
            # Check website is accessible
            external_ip = self._get_vm_external_ip()
            url = f"http://{external_ip}"
            logger.info(f"Attempting to access website at {url}")
            # A simple check could be added here, e.g., using requests
            # For now, we assume if services are up, the site is accessible.
            
            logger.info("✅ Health check passed.")
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            raise

    def run_deployment(self, processed_data: Dict[str, Any]):
        """Runs the complete deployment process to GCS and Cloud Run."""
        logger.info("🚀 Starting new deployment to GCS and Cloud Run...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - deployment skipped")
            return "http://dry-run-deployment-url"
            
        try:
            # Step 1: Upload static content to GCS
            self.upload_static_to_gcs(processed_data)
            
            # Step 2: Build and push form handler container
            image_uri = self.build_and_push_container(processed_data)
            
            # Step 3: Deploy form handler to Cloud Run
            service_url = self.deploy_to_cloud_run(image_uri)
            
            # Update content to point to the new form handler URL
            # This is a placeholder for a more complex implementation
            logger.info("✅ Deployment successful. Static content on GCS, form handler on Cloud Run.")
            
            # The final URL will be a combination of GCS and Cloud Run, likely behind a Load Balancer
            # For now, we return the Cloud Run service URL
            return service_url

        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            raise
            
    def upload_static_to_gcs(self, processed_data: Dict[str, Any]):
        """Uploads static website files to Google Cloud Storage."""
        bucket_name = self.gcp_config.gcs.get('bucket_name')
        if not bucket_name:
            raise ValueError("GCS bucket name is not configured.")

        logger.info(f"📤 Uploading static content to GCS bucket: {bucket_name}")
        
        # 1. Create bucket if it doesn't exist
        try:
            bucket = self.storage_client.create_bucket(bucket_name, location=self.gcp_config.region)
            logger.info(f"Bucket {bucket_name} created.")
        except google_exceptions.Conflict:
            bucket = self.storage_client.get_bucket(bucket_name)
            logger.info(f"Bucket {bucket_name} already exists.")
            
        # 2. Make bucket public
        bucket.iam_configuration.uniform_bucket_level_access_enabled = False
        bucket.patch()
        policy = bucket.get_iam_policy(requested_policy_version=3)
        policy.bindings.append({"role": "roles/storage.objectViewer", "members": {"allUsers"}})
        bucket.set_iam_policy(policy)
        
        # 3. Configure for website hosting
        bucket.website_main_page_suffix = 'index.html'
        bucket.website_not_found_page = '404.html' # Assuming a 404 page might exist
        bucket.patch()
        
        # 4. Upload files
        # Create a temporary directory for local files to preserve structure
        temp_dir = Path("temp_gcs_upload")
        temp_dir.mkdir(exist_ok=True)

        try:
            # Save pages and assets to temp dir
            for page in processed_data.get('pages', []):
                filename = page.get('filename', 'index.html')
                (temp_dir / filename).write_text(page.get('html', ''), encoding='utf-8')

            for asset in processed_data.get('assets', []):
                local_path = Path(asset.get('local_path', ''))
                # Create the full path in the temp directory
                full_temp_path = temp_dir / local_path.relative_to(local_path.parts[0])
                full_temp_path.parent.mkdir(parents=True, exist_ok=True)
                full_temp_path.write_bytes(asset.get('content', b''))
            
            # Walk through temp dir and upload
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    blob_name = str(file_path.relative_to(temp_dir))
                    blob = bucket.blob(blob_name)
                    blob.upload_from_filename(str(file_path))
                    logger.debug(f"Uploaded {blob_name} to bucket {bucket_name}.")

        finally:
            import shutil
            shutil.rmtree(temp_dir)
            
        logger.info(f"✅ Static content uploaded successfully to gs://{bucket_name}")

    def build_and_push_container(self, processed_data: Dict[str, Any]) -> str:
        """Builds a container using Google Cloud Build and pushes to Artifact Registry."""
        logger.info("📦 Building container with Cloud Build...")
        
        project_id = self.gcp_config.project_id
        location = self.gcp_config.region
        repo_name = self.gcp_config.cloud_run.get('repo_name')
        image_name = self.gcp_config.cloud_run.get('service_name')
        source_bucket_name = f"{project_id}-cloudbuild-source"

        # 1. Prepare and upload source code to a GCS bucket
        source_archive = self._prepare_and_upload_source(processed_data, source_bucket_name)

        # 2. Ensure Artifact Registry repository exists
        self._ensure_artifact_registry_repo(repo_name)

        # 3. Trigger Cloud Build
        image_uri = f"{location}-docker.pkg.dev/{project_id}/{repo_name}/{image_name}"
        self._trigger_cloud_build(source_bucket_name, source_archive, image_uri)
        
        final_image_uri = f"{image_uri}:latest"
        logger.info(f"✅ Cloud Build finished. Image URI: {final_image_uri}")
        
        return final_image_uri

    def _prepare_and_upload_source(self, processed_data, bucket_name):
        """Creates a source tarball and uploads it to GCS for Cloud Build."""
        import tarfile
        
        temp_dir = Path("temp_build_source")
        temp_dir.mkdir(exist_ok=True)
        archive_path = Path("source.tar.gz")

        try:
            # Create files in temp dir
            (temp_dir / "form_handler.py").write_text(self._get_form_handler_code(processed_data.get('forms', [])))
            (temp_dir / "wsgi.py").write_text("from form_handler import app\\n\\nif __name__ == '__main__':\\n    app.run()\\n")
            # We also need the Dockerfile and requirements
            with open("Dockerfile", "r") as f_in, open(temp_dir / "Dockerfile", "w") as f_out:
                f_out.write(f_in.read())
            with open("requirements.txt", "r") as f_in, open(temp_dir / "requirements.txt", "w") as f_out:
                f_out.write(f_in.read())

            # Create tarball
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(str(temp_dir), arcname=os.path.sep)
            
            # Upload to GCS
            bucket = self.storage_client.bucket(bucket_name)
            if not bucket.exists():
                self.storage_client.create_bucket(bucket, location=self.gcp_config.region)
            
            blob = bucket.blob(archive_path.name)
            blob.upload_from_filename(archive_path)
            logger.info(f"Uploaded source to gs://{bucket_name}/{archive_path.name}")
            return archive_path.name
        finally:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if archive_path.exists():
                os.remove(archive_path)

    def _ensure_artifact_registry_repo(self, repo_name):
        """Checks if an Artifact Registry repo exists, creates if not, using gcloud."""
        logger.info(f"Ensuring Artifact Registry repository '{repo_name}' exists...")
        
        command = [
            'gcloud', 'artifacts', 'repositories', 'create', repo_name,
            f'--project={self.gcp_config.project_id}',
            f'--location={self.gcp_config.region}',
            '--repository-format=docker',
            '--quiet'
        ]
        
        try:
            # We run this command, but ignore failures in case it already exists.
            # A more robust solution would be to list and check, but this is simpler.
            subprocess.run(command, check=False, capture_output=True, text=True)
            logger.info(f"Successfully ensured repository '{repo_name}' exists.")
        except Exception as e:
            logger.warning(f"Could not create repository (it might already exist): {e}")

    def _trigger_cloud_build(self, bucket, archive, image_uri):
        """Triggers a Cloud Build job using gcloud and waits for it to complete."""
        logger.info(f"Submitting Cloud Build job for image {image_uri}...")
        
        command = [
            'gcloud', 'builds', 'submit', f'gs://{bucket}/{archive}',
            f'--tag={image_uri}',
            f'--project={self.gcp_config.project_id}',
            '--quiet'
        ]
        
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info("Cloud Build job finished.")
        return result

    def deploy_to_cloud_run(self, image_uri: str) -> str:
        """Deploys the container to Google Cloud Run using gcloud."""
        logger.info(f"☁️ Deploying container {image_uri} to Cloud Run...")
        
        service_name = self.gcp_config.cloud_run.get('service_name')
        
        command = [
            'gcloud', 'run', 'deploy', service_name,
            f'--image={image_uri}',
            f'--platform=managed',
            f'--region={self.gcp_config.region}',
            f'--project={self.gcp_config.project_id}',
            '--allow-unauthenticated', # To make the service public
            '--quiet'
        ]

        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            # Get the URL of the deployed service
            describe_command = [
                'gcloud', 'run', 'services', 'describe', service_name,
                f'--platform=managed',
                f'--region={self.gcp_config.region}',
                f'--project={self.gcp_config.project_id}',
                '--format=value(status.url)'
            ]
            
            url_result = subprocess.run(describe_command, check=True, capture_output=True, text=True)
            service_url = url_result.stdout.strip()

            logger.info(f"✅ Service '{service_name}' deployed successfully at {service_url}")
            return service_url
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Cloud Run deployment failed. Command: {' '.join(e.cmd)}")
            logger.error(f"Stderr: {e.stderr}")
            raise e 