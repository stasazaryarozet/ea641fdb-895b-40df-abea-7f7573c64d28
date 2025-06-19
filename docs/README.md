# Tilda to Google Cloud Migration Agent - Документация

## Обзор

Автономный ИИ-агент для переноса сайтов с платформы Tilda на Google Cloud Platform. Агент автоматически извлекает все ресурсы с Tilda, обрабатывает их и развертывает на виртуальной машине в Google Cloud.

## Архитектура

### Основные компоненты

1. **Extractors** - Извлечение данных с Tilda
   - `TildaExtractor` - Основной класс для работы с Tilda API
   - Извлечение страниц, ресурсов и форм

2. **Processors** - Обработка контента
   - `ContentProcessor` - Обработка и оптимизация контента
   - Минификация CSS/JS, оптимизация изображений
   - Замена Tilda-специфичных элементов

3. **Deployers** - Развертывание на Google Cloud
   - `GoogleCloudDeployer` - Создание и настройка VM
   - Настройка веб-сервера (nginx)
   - Настройка SSL сертификатов

4. **Form Handlers** - Обработка форм
   - `FormHandler` - Обработка отправки форм
   - Поддержка SendGrid и SMTP
   - Валидация полей

5. **Utils** - Утилиты
   - Логирование
   - Вспомогательные функции
   - Работа с файлами

## Установка и настройка

### Требования

- Python 3.8+
- Google Cloud SDK
- Доступ к Tilda API
- Docker (опционально)

### Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd tilda-migration-agent

# Установка зависимостей
pip install -r requirements.txt

# Настройка Google Cloud SDK
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Настройка конфигурации

1. Скопируйте пример конфигурации:
```bash
cp config.example.yaml config.yaml
```

2. Отредактируйте `config.yaml`:
   - Добавьте ваши Tilda API ключи
   - Настройте Google Cloud параметры
   - Укажите настройки для обработки форм

3. Настройте переменные окружения (опционально):
```bash
export TILDA_API_KEY="your_api_key"
export TILDA_SECRET_KEY="your_secret_key"
export GOOGLE_CLOUD_PROJECT="your_project_id"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
export SENDGRID_API_KEY="your_sendgrid_key"
```

## Использование

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

### Проверка конфигурации

```bash
python src/main.py validate --config config.yaml
```

### Dry-run режим

```bash
python src/main.py migrate --config config.yaml --dry-run
```

## Конфигурация

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
  project_id: "your-gcp-project-id"
  region: "us-central1"
  zone: "us-central1-a"
  credentials_file: "path/to/service-account-key.json"
  
  vm:
    name: "tilda-migrated-site"
    machine_type: "e2-micro"
    disk_size_gb: 20
    image_family: "debian-11"
    image_project: "debian-cloud"
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

## Процесс миграции

### 1. Извлечение данных с Tilda

Агент извлекает:
- HTML страницы
- CSS и JavaScript файлы
- Изображения и другие ресурсы
- Формы и их конфигурации

### 2. Обработка контента

- Удаление Tilda-специфичных элементов
- Оптимизация изображений
- Минификация CSS/JS
- Обновление ссылок на ресурсы

### 3. Развертывание на Google Cloud

- Создание виртуальной машины
- Настройка nginx веб-сервера
- Загрузка обработанного контента
- Настройка SSL сертификатов

### 4. Настройка обработки форм

- Развертывание Flask приложения
- Настройка эндпоинтов для форм
- Интеграция с почтовыми сервисами

## Мониторинг и логирование

### Логи

Логи сохраняются в файл `logs/migration.log` с ротацией:
- Максимальный размер файла: 10 MB
- Хранение: 7 дней
- Сжатие старых логов

### Мониторинг

Агент настраивает базовый мониторинг:
- Установка утилит мониторинга (htop, iotop, nethogs)
- Проверка состояния сервисов

### Резервное копирование

Автоматическое резервное копирование:
- Ежедневные бэкапы в 2:00
- Хранение последних 7 бэкапов
- Сжатие в tar.gz формат

## Устранение неполадок

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

Включите подробное логирование:
```bash
python src/main.py migrate --config config.yaml --verbose
```

### Восстановление

Агент создает бэкапы на каждом этапе:
- Конфигурационные файлы
- Извлеченные данные
- Обработанный контент

## Безопасность

### Рекомендации

1. Используйте переменные окружения для секретных данных
2. Ограничьте права сервисного аккаунта Google Cloud
3. Регулярно обновляйте SSL сертификаты
4. Настройте файрвол для VM

### SSL сертификаты

Агент автоматически настраивает SSL с помощью Let's Encrypt:
- Автоматическое получение сертификатов
- Автоматическое обновление
- Поддержка wildcard доменов

## Расширение функциональности

### Добавление новых провайдеров

Для добавления поддержки других облачных провайдеров:
1. Создайте новый класс в `deployers/`
2. Реализуйте интерфейс `BaseDeployer`
3. Добавьте конфигурацию

### Кастомная обработка форм

Для кастомной логики обработки форм:
1. Создайте новый обработчик в `form_handlers/`
2. Настройте маршрутизацию
3. Обновите конфигурацию

## Лицензия

MIT License - см. файл LICENSE для деталей.

## Поддержка

Для получения поддержки:
1. Проверьте документацию
2. Изучите логи ошибок
3. Создайте issue в репозитории 