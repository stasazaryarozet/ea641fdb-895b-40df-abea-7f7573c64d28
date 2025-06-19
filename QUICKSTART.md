# 🚀 Быстрый старт - Tilda Migration Agent

## Установка за 5 минут

### 1. Клонирование и установка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd tilda-migration-agent

# Запустите автоматическую установку
./scripts/install.sh
```

### 2. Настройка конфигурации

Отредактируйте `config.yaml`:

```yaml
# Tilda Configuration
tilda:
  api_key: "ВАШ_TILDA_API_KEY"
  secret_key: "ВАШ_TILDA_SECRET_KEY"
  project_id: "ВАШ_TILDA_PROJECT_ID"
  base_url: "https://ваш-сайт.tilda.ws"

# Google Cloud Configuration
google_cloud:
  project_id: "ВАШ_GCP_PROJECT_ID"
  region: "us-central1"
  zone: "us-central1-a"
  credentials_file: "path/to/service-account-key.json"
```

### 3. Настройка Google Cloud

```bash
# Аутентификация в Google Cloud
gcloud auth login

# Установка проекта
gcloud config set project ВАШ_GCP_PROJECT_ID

# Создание сервисного аккаунта (если нужно)
gcloud iam service-accounts create tilda-migration \
    --display-name="Tilda Migration Agent"

# Создание ключа
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=tilda-migration@ВАШ_GCP_PROJECT_ID.iam.gserviceaccount.com

# Назначение ролей
gcloud projects add-iam-policy-binding ВАШ_GCP_PROJECT_ID \
    --member="serviceAccount:tilda-migration@ВАШ_GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/compute.admin"

gcloud projects add-iam-policy-binding ВАШ_GCP_PROJECT_ID \
    --member="serviceAccount:tilda-migration@ВАШ_GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

### 4. Запуск миграции

```bash
# Активация виртуального окружения
source venv/bin/activate

# Проверка конфигурации
python src/main.py validate

# Запуск полной миграции
python src/main.py migrate
```

## Пошаговый процесс

### Шаг 1: Извлечение данных
```bash
python src/main.py extract
```
Агент извлечет:
- ✅ HTML страницы
- ✅ CSS и JavaScript файлы  
- ✅ Изображения и ресурсы
- ✅ Формы и их настройки

### Шаг 2: Развертывание
```bash
python src/main.py deploy
```
Агент создаст:
- ✅ Виртуальную машину в Google Cloud
- ✅ Веб-сервер nginx
- ✅ SSL сертификат
- ✅ Обработчик форм

### Шаг 3: Проверка
```bash
# Проверка статуса
python src/main.py validate

# Просмотр логов
tail -f logs/migration.log
```

## Режимы работы

### Полная миграция
```bash
python src/main.py migrate
```

### Только извлечение
```bash
python src/main.py extract
```

### Только развертывание
```bash
python src/main.py deploy
```

### Dry-run (тестовый режим)
```bash
python src/main.py migrate --dry-run
```

### Подробное логирование
```bash
python src/main.py migrate --verbose
```

## Структура файлов после миграции

```
extracted_data/
├── pages.json          # Извлеченные страницы
├── assets.json         # Извлеченные ресурсы
└── forms.json          # Извлеченные формы

form_handler/
├── app.py              # Flask приложение для форм
├── config.json         # Конфигурация форм
└── forms.json          # Настройки форм

logs/
└── migration.log       # Логи миграции
```

## Мониторинг

### Просмотр логов
```bash
# Все логи
cat logs/migration.log

# Последние 100 строк
tail -100 logs/migration.log

# Логи в реальном времени
tail -f logs/migration.log
```

### Проверка статуса VM
```bash
# Список VM
gcloud compute instances list

# Подключение к VM
gcloud compute ssh www-data@tilda-migrated-site --zone=us-central1-a

# Проверка сервисов
sudo systemctl status nginx
sudo systemctl status form-handler
```

## Устранение неполадок

### Ошибка аутентификации Google Cloud
```bash
# Проверка аутентификации
gcloud auth list

# Повторная аутентификация
gcloud auth login
```

### Ошибка Tilda API
```bash
# Проверка API ключей
python src/main.py validate
```

### Ошибка развертывания
```bash
# Проверка квот
gcloud compute regions describe us-central1

# Проверка средств
gcloud billing accounts list
```

## Полезные команды

### Очистка
```bash
# Удаление VM
gcloud compute instances delete tilda-migrated-site --zone=us-central1-a

# Очистка данных
rm -rf extracted_data/
rm -rf form_handler/
```

### Бэкап
```bash
# Создание бэкапа
tar -czf backup-$(date +%Y%m%d).tar.gz extracted_data/ form_handler/

# Восстановление
tar -xzf backup-20241201.tar.gz
```

## Поддержка

- 📖 [Полная документация](docs/README.md)
- 🐛 [Сообщить об ошибке](https://github.com/your-org/tilda-migration-agent/issues)
- 💬 [Задать вопрос](https://github.com/your-org/tilda-migration-agent/discussions)

---

**Готово!** Ваш сайт с Tilda теперь работает на Google Cloud! 🎉 