# 🚀 Инструкции по запуску Tilda Migration Agent

## 📋 Предварительные требования

### Системные требования
- **ОС**: Linux, macOS, Windows (с WSL)
- **Python**: 3.8 или выше
- **RAM**: Минимум 2 GB
- **Диск**: Минимум 1 GB свободного места

### Необходимые аккаунты и ключи
- ✅ **Tilda API ключи** (api_key, secret_key, project_id)
- ✅ **Google Cloud аккаунт** с активным проектом
- ✅ **Google Cloud сервисный аккаунт** с правами на Compute Engine
- ✅ **SendGrid API ключ** (опционально, для email уведомлений)

## 🔧 Установка

### Автоматическая установка (рекомендуется)

```bash
# 1. Клонирование репозитория
git clone <repository-url>
cd tilda-migration-agent

# 2. Запуск автоматической установки
chmod +x scripts/install.sh
./scripts/install.sh
```

### Ручная установка

```bash
# 1. Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# 2. Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# 3. Установка пакета
pip install -e .

# 4. Создание необходимых директорий
mkdir -p logs extracted_data form_handler
```

## ⚙️ Настройка

### 1. Настройка Google Cloud

```bash
# Аутентификация в Google Cloud
gcloud auth login

# Установка проекта
gcloud config set project YOUR_PROJECT_ID

# Создание сервисного аккаунта
gcloud iam service-accounts create tilda-migration \
    --display-name="Tilda Migration Agent"

# Создание ключа сервисного аккаунта
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=tilda-migration@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Назначение необходимых ролей
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:tilda-migration@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/compute.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:tilda-migration@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

### 2. Настройка конфигурации

```bash
# Копирование примера конфигурации
cp config.example.yaml config.yaml

# Редактирование конфигурации
nano config.yaml  # или любой текстовый редактор
```

**Обязательные настройки в config.yaml:**

```yaml
tilda:
  api_key: "ВАШ_TILDA_API_KEY"
  secret_key: "ВАШ_TILDA_SECRET_KEY"
  project_id: "ВАШ_TILDA_PROJECT_ID"
  base_url: "https://ваш-сайт.tilda.ws"

google_cloud:
  project_id: "ВАШ_GCP_PROJECT_ID"
  credentials_file: "service-account-key.json"
```

### 3. Настройка переменных окружения (опционально)

```bash
# Создание файла .env
cat > .env << EOF
TILDA_API_KEY=ваш_api_key
TILDA_SECRET_KEY=ваш_secret_key
GOOGLE_CLOUD_PROJECT=ваш_project_id
GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json
SENDGRID_API_KEY=ваш_sendgrid_key
EOF

# Загрузка переменных
source .env
```

## 🚀 Запуск

### 1. Проверка конфигурации

```bash
# Активация виртуального окружения
source venv/bin/activate

# Проверка конфигурации
python src/main.py validate
```

**Ожидаемый результат:**
```
✅ Конфигурация проверена
✅ Tilda API connection successful
✅ Google Cloud connection successful
```

### 2. Тестовый запуск (dry-run)

```bash
# Запуск в тестовом режиме
python src/main.py migrate --dry-run --verbose
```

**Ожидаемый результат:**
```
🚀 Запуск миграции Tilda → Google Cloud
🔍 Dry run mode - VM creation skipped
🔍 Dry run mode - content upload skipped
✅ Миграция завершена успешно!
```

### 3. Полный запуск

```bash
# Запуск полной миграции
python src/main.py migrate --verbose
```

**Ожидаемый результат:**
```
🚀 Запуск миграции Tilda → Google Cloud

1️⃣ Проверка конфигурации...
✅ Конфигурация проверена

2️⃣ Извлечение данных с Tilda...
📄 Извлечено 5 страниц
📦 Извлечено 23 ресурса
📝 Извлечено 2 формы

3️⃣ Обработка контента...
📄 Страницы обработаны
📦 Ресурсы обработаны
📝 Формы обработаны

4️⃣ Развертывание на Google Cloud...
🖥️ Виртуальная машина создана
📤 Контент загружен
🌐 Веб-сервер настроен
🔒 SSL сертификат настроен

5️⃣ Настройка обработки форм...
📝 Обработчик форм развернут
🔗 Эндпоинты настроены

6️⃣ Финальная настройка...
📊 Мониторинг настроен
💾 Резервное копирование настроено
✅ Проверка работоспособности

✅ Миграция завершена успешно!
🌐 Сайт доступен по адресу: http://34.123.45.67
```

## 📊 Мониторинг процесса

### Просмотр логов в реальном времени

```bash
# Просмотр логов
tail -f logs/migration.log

# Просмотр последних 100 строк
tail -100 logs/migration.log

# Поиск ошибок
grep -i error logs/migration.log
```

### Проверка статуса VM

```bash
# Список VM в проекте
gcloud compute instances list

# Подключение к VM
gcloud compute ssh www-data@tilda-migrated-site --zone=us-central1-a

# Проверка сервисов на VM
sudo systemctl status nginx
sudo systemctl status form-handler
```

## 🔍 Отладка

### Частые проблемы и решения

#### 1. Ошибка аутентификации Google Cloud
```bash
# Проверка аутентификации
gcloud auth list

# Повторная аутентификация
gcloud auth login

# Проверка проекта
gcloud config get-value project
```

#### 2. Ошибка Tilda API
```bash
# Проверка API ключей
python src/main.py validate

# Тест подключения к Tilda
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.tildacdn.info/getprojectexport?projectid=YOUR_PROJECT_ID"
```

#### 3. Ошибка создания VM
```bash
# Проверка квот
gcloud compute regions describe us-central1

# Проверка средств
gcloud billing accounts list

# Проверка прав сервисного аккаунта
gcloud projects get-iam-policy YOUR_PROJECT_ID
```

#### 4. Ошибка загрузки контента
```bash
# Проверка доступности VM
gcloud compute instances describe tilda-migrated-site --zone=us-central1-a

# Проверка файлов на VM
gcloud compute ssh www-data@tilda-migrated-site --zone=us-central1-a \
    --command="ls -la /var/www/html/"
```

## 🧹 Очистка

### Удаление созданных ресурсов

```bash
# Удаление VM
gcloud compute instances delete tilda-migrated-site --zone=us-central1-a

# Удаление сервисного аккаунта
gcloud iam service-accounts delete \
    tilda-migration@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Очистка локальных данных
rm -rf extracted_data/
rm -rf form_handler/
rm -f service-account-key.json
```

### Сброс конфигурации

```bash
# Создание бэкапа текущей конфигурации
cp config.yaml config.yaml.backup

# Возврат к примеру конфигурации
cp config.example.yaml config.yaml
```

## 📞 Получение помощи

### Документация
- 📖 [Полная документация](docs/README.md)
- 🚀 [Быстрый старт](QUICKSTART.md)
- 📋 [Информация о проекте](PROJECT_INFO.md)

### Поддержка
- 🐛 [GitHub Issues](https://github.com/your-org/tilda-migration-agent/issues)
- 💬 [GitHub Discussions](https://github.com/your-org/tilda-migration-agent/discussions)
- 📧 [Email поддержка](mailto:support@example.com)

### Полезные команды

```bash
# Справка по командам
python src/main.py --help

# Справка по конкретной команде
python src/main.py migrate --help

# Проверка версии
python src/main.py --version

# Список всех доступных команд
python src/main.py --help
```

---

**🎉 Готово! Ваш Tilda Migration Agent готов к работе!** 