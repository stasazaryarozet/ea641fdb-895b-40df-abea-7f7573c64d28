import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.deployers.google_cloud_deployer import GoogleCloudDeployer
from src.core.config import load_config

@patch('src.deployers.google_cloud_deployer.service_account.Credentials.from_service_account_file')
@patch('src.deployers.google_cloud_deployer.discovery.build')
class TestGoogleCloudDeployer(unittest.TestCase):

    def setUp(self):
        """Настройка тестового окружения."""
        self.config = load_config('config.example.yaml')
        self.config.google_cloud.credentials_file = "mock_credentials.json"
        
    def test_create_vm_instance_call(self, mock_discovery_build, mock_from_service_account_file):
        """
        Тестирует, что метод создания VM вызывает правильные команды SDK.
        """
        # --- Mocking ---
        mock_creds = MagicMock()
        mock_from_service_account_file.return_value = mock_creds
        
        mock_compute = MagicMock()
        mock_discovery_build.return_value = mock_compute
        
        mock_response = MagicMock()
        mock_response.execute.return_value = {'name': 'test-operation'}
        mock_compute.instances().insert.return_value = mock_response
        mock_compute.zoneOperations().wait.return_value.execute.return_value = {"status": "DONE"}
        
        # --- Execution ---
        deployer = GoogleCloudDeployer(self.config.google_cloud)
        deployer.create_vm_instance()

        # --- Assertions ---
        mock_from_service_account_file.assert_called_once_with(
            "mock_credentials.json",
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        mock_discovery_build.assert_called_once_with('compute', 'v1', credentials=mock_creds)
        mock_compute.instances().insert.assert_called_once()
        
        call_args, call_kwargs = mock_compute.instances().insert.call_args
        vm_body = call_kwargs['body']
        
        gcp_config = self.config.google_cloud
        self.assertEqual(vm_body['name'], gcp_config.vm.name)
        self.assertIn(gcp_config.vm.machine_type, vm_body['machineType'])
        self.assertEqual(vm_body['disks'][0]['initializeParams']['diskSizeGb'], str(gcp_config.vm.disk_size_gb))


if __name__ == '__main__':
    unittest.main() 