# 🚀 Tilda to Google Cloud Migration Agent

**Автономный ИИ-агент для переноса сайтов с платформы Tilda на Google Cloud Platform**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Beta](https://img.shields.io/badge/Status-Beta-orange.svg)](https://github.com/your-org/tilda-migration-agent)

## 🌟 Возможности

- 🔍 **Автоматическое извлечение ресурсов** с Tilda (HTML, CSS, JS, изображения)
- 🎨 **Воспроизведение дизайна** и структуры сайта
- 📝 **Обработка форм** с заменой Tilda-интеграций
- ☁️ **Автоматическое развертывание** на Google Cloud
- 🔒 **Настройка HTTPS** и безопасности
- 📊 **Подробное логирование** всех операций
- 🤖 **Минимальное участие пользователя** - только для аутентификации

## 🏗️ Архитектура

```
src/
├── core/           # Основная логика агента
│   ├── agent.py    # Главный класс агента
│   └── config.py   # Управление конфигурацией
├── extractors/     # Извлечение ресурсов с Tilda
│   └── tilda_extractor.py
├── processors/     # Обработка и модификация контента
│   └── content_processor.py
├── deployers/      # Развертывание на Google Cloud
│   └── google_cloud_deployer.py
├── form_handlers/  # Обработка форм
│   └── form_handler.py
└── utils/          # Утилиты и хелперы
    ├── logger.py   # Логирование
    └── helpers.py  # Вспомогательные функции
```

## ⚡ Быстрый старт

### 1. Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd tilda-migration-agent

# Автоматическая установка
./scripts/install.sh
```

### 2. Настройка

```bash
# Копирование конфигурации
cp config.example.yaml config.yaml

# Редактирование настроек
nano config.yaml
```

### 3. Запуск

```bash
# Активация окружения
source venv/bin/activate

# Проверка конфигурации
python src/main.py validate

# Запуск миграции
python src/main.py migrate
```

## 📖 Использование

### Полная миграция
```bash
python src/main.py migrate --config config.yaml
```

### Только извлечение данных
```bash
python src/main.py extract --config config.yaml
```

### Только развертывание
```bash
python src/main.py deploy --config config.yaml
```

### Dry-run режим (тестирование)
```bash
python src/main.py migrate --config config.yaml --dry-run
```

### Подробное логирование
```bash
python src/main.py migrate --config config.yaml --verbose
```

## ⚙️ Конфигурация

### Tilda Configuration
```yaml
tilda:
  api_key: "your_tilda_api_key"
  secret_key: "your_tilda_secret_key"
  project_id: "your_tilda_project_id"
  base_url: "https://your-site.tilda.ws"
```

### Google Cloud Configuration
```yaml
google_cloud:
  project_id: "your-gcp-project_id"
  region: "us-central1"
  zone: "us-central1-a"
  credentials_file: "path/to/service-account-key.json"
  
  vm:
    name: "tilda-migrated-site"
    machine_type: "e2-micro"
    disk_size_gb: 20
```

### Form Handling Configuration
```yaml
forms:
  email_service: "sendgrid"  # or "smtp"
  sendgrid_api_key: "your_sendgrid_api_key"
  smtp:
    host: "smtp.gmail.com"
    port: 587
    username: "your_email@gmail.com"
    password: "your_app_password"
```

## 🔄 Процесс миграции

### 1. Извлечение данных с Tilda
- 📄 HTML страницы
- 🎨 CSS и JavaScript файлы
- 🖼️ Изображения и ресурсы
- 📝 Формы и их конфигурации

### 2. Обработка контента
- 🧹 Удаление Tilda-специфичных элементов
- 🖼️ Оптимизация изображений
- 📦 Минификация CSS/JS
- 🔗 Обновление ссылок на ресурсы

### 3. Развертывание на Google Cloud
- 🖥️ Создание виртуальной машины
- 🌐 Настройка nginx веб-сервера
- 📤 Загрузка обработанного контента
- 🔒 Настройка SSL сертификатов

### 4. Настройка обработки форм
- 🐍 Развертывание Flask приложения
- 🔗 Настройка эндпоинтов для форм
- 📧 Интеграция с почтовыми сервисами

## 📊 Мониторинг и логирование

### Логи
- 📁 Файл: `logs/migration.log`
- 🔄 Ротация: 10 MB
- 📅 Хранение: 7 дней
- 📦 Сжатие: ZIP

### Мониторинг
- 📈 Утилиты: htop, iotop, nethogs
- 🔍 Проверка состояния сервисов
- 📊 Автоматические уведомления

### Резервное копирование
- ⏰ Ежедневные бэкапы в 2:00
- 📦 Хранение последних 7 бэкапов
- 🗜️ Сжатие в tar.gz формат

## 🛠️ Требования

- **Python**: 3.8+
- **Google Cloud SDK**: Последняя версия
- **Tilda API**: Доступ к API
- **Docker**: Опционально

## 📚 Документация

- 📖 [Полная документация](docs/README.md)
- 🚀 [Быстрый старт](QUICKSTART.md)
- 🧪 [Примеры использования](examples/)
- 🧪 [Тесты](tests/)

## 🔧 Разработка

### Установка для разработки
```bash
# Клонирование
git clone <repository-url>
cd tilda-migration-agent

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
pip install -e .

# Установка зависимостей для разработки
pip install pytest black flake8
```

### Запуск тестов
```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src

# Конкретный тест
pytest tests/test_extractor.py
```

### Форматирование кода
```bash
# Форматирование
black src/ tests/

# Проверка стиля
flake8 src/ tests/
```

## 🐛 Устранение неполадок

### Частые проблемы

1. **Ошибка аутентификации Google Cloud**
   - Проверьте файл сервисного аккаунта
   - Убедитесь, что проект активен

2. **Ошибка Tilda API**
   - Проверьте API ключи
   - Убедитесь, что проект существует

3. **Ошибка развертывания**
   - Проверьте квоты Google Cloud
   - Убедитесь в наличии средств на аккаунте

### Отладка
```bash
# Подробное логирование
python src/main.py migrate --verbose

# Просмотр логов
tail -f logs/migration.log

# Проверка конфигурации
python src/main.py validate
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Добавьте тесты
5. Отправьте pull request

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🆘 Поддержка

- 📖 [Документация](docs/README.md)
- 🐛 [Issues](https://github.com/your-org/tilda-migration-agent/issues)
- 💬 [Discussions](https://github.com/your-org/tilda-migration-agent/discussions)
- 📧 [Email](mailto:support@example.com)

## 🙏 Благодарности

- [Tilda](https://tilda.cc/) - за отличную платформу
- [Google Cloud](https://cloud.google.com/) - за облачную инфраструктуру
- [Python Community](https://www.python.org/) - за замечательный язык

---

**Сделано с ❤️ для сообщества разработчиков**
