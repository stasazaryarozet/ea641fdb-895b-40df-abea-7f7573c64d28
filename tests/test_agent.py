import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.agent import MigrationAgent

class TestMigrationAgent(unittest.TestCase):

    @patch('src.core.agent.GoogleCloudDeployer')
    @patch('src.core.agent.ContentProcessor')
    @patch('src.core.agent.TildaExtractor')
    @patch('src.core.agent.load_config')
    def test_migration_run_orchestration(self, mock_load_config, mock_tilda_extractor, mock_content_processor, mock_gcp_deployer):
        """
        Тестирует правильность оркестрации (последовательности вызовов) в методе run.
        """
        # --- Mocking ---
        # Настраиваем моки, чтобы они возвращали нужные объекты
        mock_extractor_instance = MagicMock()
        mock_processor_instance = MagicMock()
        mock_deployer_instance = MagicMock()
        
        mock_tilda_extractor.return_value = mock_extractor_instance
        mock_content_processor.return_value = mock_processor_instance
        mock_gcp_deployer.return_value = mock_deployer_instance

        # Настраиваем возвращаемые значения для методов
        mock_extractor_instance.get_pages_list.return_value = [{'id': '1', 'title': 'Home'}]
        mock_extractor_instance.get_page_full_export.return_value = {
            'id': '1', 'html': '<html>...</html>'
        }
        mock_processor_instance.relativize_links.return_value = "<html>...rel...</html>"
        mock_processor_instance.remove_tilda_elements.return_value = "<html>...clean...</html>"

        # --- Execution ---
        # Используем реальный путь к конфигу, так как load_config тоже замокан
        agent = MigrationAgent(config_path='config.yaml', dry_run=True)
        agent.run()

        # --- Assertions ---
        # Проверяем, что ключевые методы были вызваны
        mock_extractor_instance.get_pages_list.assert_called_once()
        mock_extractor_instance.get_page_full_export.assert_called_once_with('1')
        mock_processor_instance.relativize_links.assert_called_once()
        mock_processor_instance.remove_tilda_elements.assert_called_once()
        
        # В режиме dry_run деплоер не должен вызываться
        mock_deployer_instance.create_vm_instance.assert_not_called()

        # --- Test with dry_run=False ---
        agent_real_run = MigrationAgent(config_path='config.yaml', dry_run=False)
        agent_real_run.run()
        mock_deployer_instance.create_vm_instance.assert_called_once()

if __name__ == '__main__':
    unittest.main() 