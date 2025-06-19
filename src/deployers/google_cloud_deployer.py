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
# Update system
apt-get update
apt-get install -y nginx python3 python3-pip git

# Install Python dependencies
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
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Restart nginx
systemctl restart nginx
systemctl enable nginx

# Create form handler service
cat > /etc/systemd/system/form-handler.service << 'EOF'
[Unit]
Description=Tilda Form Handler
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/html
ExecStart=/usr/local/bin/gunicorn -w 4 -b 127.0.0.1:5000 form_handler:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable form-handler
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
    
    def _run_gcloud_ssh_command_with_retry(self, command: List[str], retries: int = 5, delay: int = 15):
        """Run a gcloud command with retries for SSH readiness."""
        for i in range(retries):
            try:
                logger.info(f"Running command (attempt {i+1}/{retries}): {' '.join(command)}")
                subprocess.run(command, check=True, capture_output=True, text=True)
                logger.info(f"Command successful: {' '.join(command)}")
                return
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
            
            # Upload to VM using gcloud
            external_ip = self._get_vm_external_ip()
            
            # Use gcloud compute scp to upload files
            scp_command = [
                'gcloud', 'compute', 'scp',
                '--recurse', str(temp_dir),
                f'www-data@{self.vm_instance.name}:',
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id
            ]
            self._run_gcloud_ssh_command_with_retry(scp_command)
            
            # Move files to correct location
            ssh_command = [
                'gcloud', 'compute', 'ssh',
                f'www-data@{self.vm_instance.name}',
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'sudo mv temp_deploy/* /var/www/html/ && sudo chown -R www-data:www-data /var/www/html && rm -rf temp_deploy'
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
        """Generate form handler code"""
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
    
    def configure_web_server(self):
        """Configure web server"""
        logger.info("🌐 Configuring web server...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - web server configuration skipped")
            return
        
        try:
            # Restart services
            subprocess.run([
                'gcloud', 'compute', 'ssh',
                f'www-data@{self.vm_instance.name}',
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'sudo systemctl restart nginx && sudo systemctl restart form-handler'
            ], check=True)
            
            logger.info("✅ Web server configured successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to configure web server: {e}")
            raise
    
    def setup_ssl(self):
        """Setup SSL certificate"""
        logger.info("🔒 Setting up SSL certificate...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - SSL setup skipped")
            return
        
        try:
            # Install certbot
            subprocess.run([
                'gcloud', 'compute', 'ssh',
                f'www-data@{self.vm_instance.name}',
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'sudo apt-get install -y certbot python3-certbot-nginx'
            ], check=True)
            
            # Get domain from config
            domain = self.gcp_config.dns.get('domain', '')
            if domain:
                # Obtain SSL certificate
                subprocess.run([
                    'gcloud', 'compute', 'ssh',
                    f'www-data@{self.vm_instance.name}',
                    '--zone', self.gcp_config.zone,
                    '--project', self.gcp_config.project_id,
                    '--command', f'sudo certbot --nginx --agree-tos --email {self.gcp_config.ssl_email} -d {domain} --redirect --non-interactive'
                ], check=True)
            
            logger.info("✅ SSL certificate configured successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ SSL setup failed (continuing without SSL): {e}")
    
    def setup_monitoring(self):
        """Setup monitoring"""
        logger.info("📊 Setting up monitoring...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - monitoring setup skipped")
            return
        
        try:
            # Install monitoring tools
            subprocess.run([
                'gcloud', 'compute', 'ssh',
                f'www-data@{self.vm_instance.name}',
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'sudo apt-get install -y htop iotop nethogs'
            ], check=True)
            
            logger.info("✅ Monitoring configured successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Monitoring setup failed: {e}")
    
    def setup_backups(self):
        """Setup automatic backups"""
        logger.info("💾 Setting up automatic backups...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - backup setup skipped")
            return
        
        try:
            # Create backup script
            backup_script = '''#!/bin/bash
# Backup script
BACKUP_DIR="/var/backups/website"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup website files
tar -czf $BACKUP_DIR/website_$DATE.tar.gz /var/www/html

# Keep only last 7 backups
find $BACKUP_DIR -name "website_*.tar.gz" -mtime +7 -delete
'''
            
            # Upload and setup backup script
            subprocess.run([
                'gcloud', 'compute', 'ssh',
                f'www-data@{self.vm_instance.name}',
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', f'echo "{backup_script}" | sudo tee /usr/local/bin/backup-website.sh && sudo chmod +x /usr/local/bin/backup-website.sh'
            ], check=True)
            
            # Setup cron job
            subprocess.run([
                'gcloud', 'compute', 'ssh',
                f'www-data@{self.vm_instance.name}',
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'echo "0 2 * * * /usr/local/bin/backup-website.sh" | sudo crontab -'
            ], check=True)
            
            logger.info("✅ Automatic backups configured successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Backup setup failed: {e}")
    
    def health_check(self):
        """Perform health check"""
        logger.info("✅ Performing health check...")
        
        if self.dry_run:
            logger.info("🔍 Dry run mode - health check skipped")
            return
        
        try:
            external_ip = self._get_vm_external_ip()
            
            # Check if services are running
            result = subprocess.run([
                'gcloud', 'compute', 'ssh',
                f'www-data@{self.vm_instance.name}',
                '--zone', self.gcp_config.zone,
                '--project', self.gcp_config.project_id,
                '--command', 'sudo systemctl is-active nginx form-handler'
            ], capture_output=True, text=True, check=True)
            
            if 'active' in result.stdout:
                logger.info("✅ Health check passed - all services are running")
            else:
                logger.warning("⚠️ Some services are not running")
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            raise 