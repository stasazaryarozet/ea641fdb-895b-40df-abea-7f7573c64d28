"""
Form handler for Tilda migration
"""

import json
import smtplib
from pathlib import Path
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger

from core.config import FormsConfig


class FormHandler:
    """Handle form submissions"""
    
    def __init__(self, config: FormsConfig):
        self.config = config
        self.handlers = {
            'sendgrid': self._send_sendgrid_email,
            'smtp': self._send_smtp_email
        }
    
    def deploy_handler(self):
        """Deploy form handler to server"""
        logger.info("📝 Deploying form handler...")
        
        # Create form handler directory
        handler_dir = Path("form_handler")
        handler_dir.mkdir(exist_ok=True)
        
        # Create main handler file
        handler_file = handler_dir / "app.py"
        with open(handler_file, 'w', encoding='utf-8') as f:
            f.write(self._get_handler_code())
        
        # Create requirements file
        requirements_file = handler_dir / "requirements.txt"
        with open(requirements_file, 'w') as f:
            f.write("flask>=2.3.0\nsendgrid>=6.10.0\n")
        
        # Create configuration file
        config_file = handler_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({
                'email_service': self.config.email_service,
                'sendgrid_api_key': self.config.sendgrid_api_key,
                'smtp': self.config.smtp,
                'endpoints': self.config.endpoints
            }, f, indent=2)
        
        logger.info("✅ Form handler deployed successfully")
    
    def _get_handler_code(self) -> str:
        """Generate form handler code"""
        handler_code = '''#!/usr/bin/env python3
from flask import Flask, request, jsonify
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

def send_sendgrid_email(data, form_config):
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sg = SendGridAPIClient(api_key=config['sendgrid_api_key'])
        
        # Create email
        message = Mail(
            from_email=config['smtp']['username'],
            to_emails=form_config.get('email', config['smtp']['username']),
            subject='New form submission: {name}'.format(name=form_config.get("name", "Contact")),
            html_content=create_email_body(data, form_config)
        )
        
        response = sg.send(message)
        return response.status_code == 202
        
    except Exception as e:
        print("SendGrid error: {error}".format(error=e))
        return False

def send_smtp_email(data, form_config):
    try:
        msg = MIMEMultipart()
        msg['From'] = config['smtp']['username']
        msg['To'] = form_config.get('email', config['smtp']['username'])
        msg['Subject'] = 'New form submission: {name}'.format(name=form_config.get("name", "Contact"))
        
        body = create_email_body(data, form_config)
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(config['smtp']['host'], config['smtp']['port'])
        server.starttls()
        server.login(config['smtp']['username'], config['smtp']['password'])
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        print("SMTP error: {error}".format(error=e))
        return False

def create_email_body(data, form_config):
    body = """
    <html>
    <body>
        <h2>New form submission: {name}</h2>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr><th>Field</th><th>Value</th></tr>
    """.format(name=form_config.get('name', 'Contact'))
    
    for field in form_config.get('fields', []):
        field_name = field.get('name', '')
        field_value = data.get(field_name, '')
        body += "<tr><td>{field_name}</td><td>{field_value}</td></tr>".format(
            field_name=field_name, field_value=field_value
        )
    
    body += """
        </table>
    </body>
    </html>
    """
    
    return body

@app.route('/api/form-handler', methods=['POST'])
def handle_form():
    try:
        data = request.form.to_dict()
        form_type = data.get('form_type', 'contact')
        
        # Load form configurations
        forms_file = 'forms.json'
        if os.path.exists(forms_file):
            with open(forms_file, 'r') as f:
                forms = json.load(f)
        else:
            forms = []
        
        # Find form configuration
        form_config = None
        for form in forms:
            if form.get('name', '').lower() == form_type.lower():
                form_config = form
                break
        
        if not form_config:
            # Use default form configuration
            form_config = {
                'name': form_type,
                'email': config['smtp']['username'],
                'fields': [],
                'success_message': 'Form submitted successfully',
                'error_message': 'An error occurred'
            }
        
        # Validate required fields
        required_fields = [field['name'] for field in form_config.get('fields', []) if field.get('required')]
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': 'Field {field} is required'.format(field=field)}), 400
        
        # Send email
        email_sent = False
        if config['email_service'] == 'sendgrid':
            email_sent = send_sendgrid_email(data, form_config)
        else:
            email_sent = send_smtp_email(data, form_config)
        
        if email_sent:
            return jsonify({'success': True, 'message': form_config.get('success_message', 'Form submitted successfully')})
        else:
            return jsonify({'error': 'Failed to send email'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
'''
        return handler_code
    
    def configure_endpoints(self, forms: List[Dict[str, Any]]):
        """Configure form endpoints"""
        logger.info("🔗 Configuring form endpoints...")
        
        # Save forms configuration
        forms_file = Path("form_handler/forms.json")
        with open(forms_file, 'w', encoding='utf-8') as f:
            json.dump(forms, f, ensure_ascii=False, indent=2)
        
        logger.info("✅ Form endpoints configured successfully")
    
    def _send_sendgrid_email(self, data: Dict[str, Any], form_config: Dict[str, Any]) -> bool:
        """Send email using SendGrid"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            sg = SendGridAPIClient(api_key=self.config.sendgrid_api_key)
            
            # Create email
            message = Mail(
                from_email=self.config.smtp['username'],
                to_emails=form_config.get('email', self.config.smtp['username']),
                subject=f"New form submission: {form_config.get('name', 'Contact')}",
                html_content=self._create_email_body(data, form_config)
            )
            
            response = sg.send(message)
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return False
    
    def _send_smtp_email(self, data: Dict[str, Any], form_config: Dict[str, Any]) -> bool:
        """Send email using SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.smtp['username']
            msg['To'] = form_config.get('email', self.config.smtp['username'])
            msg['Subject'] = f"New form submission: {form_config.get('name', 'Contact')}"
            
            body = self._create_email_body(data, form_config)
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.config.smtp['host'], self.config.smtp['port'])
            server.starttls()
            server.login(self.config.smtp['username'], self.config.smtp['password'])
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False
    
    def _create_email_body(self, data: Dict[str, Any], form_config: Dict[str, Any]) -> str:
        """Create email body"""
        body = f"""
        <html>
        <body>
            <h2>New form submission: {form_config.get('name', 'Contact')}</h2>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr><th>Field</th><th>Value</th></tr>
        """
        
        for field in form_config.get('fields', []):
            field_name = field.get('name', '')
            field_value = data.get(field_name, '')
            body += f"<tr><td>{field_name}</td><td>{field_value}</td></tr>"
        
        body += """
            </table>
        </body>
        </html>
        """
        
        return body
    
    def send_email(self, data: Dict[str, Any], form_config: Dict[str, Any]) -> bool:
        """Send email using configured service"""
        handler = self.handlers.get(self.config.email_service)
        if handler:
            return handler(data, form_config)
        else:
            logger.error(f"Unknown email service: {self.config.email_service}")
            return False 