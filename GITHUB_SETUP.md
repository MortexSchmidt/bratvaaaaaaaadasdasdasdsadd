# Настройка GitHub репозитория

## Создание нового репозитория

1. Войдите в ваш аккаунт GitHub
2. Нажмите "New repository" или "+" → "New repository"
3. Введите имя репозитория (например, "telegram-truth-or-dare-bot")
4. Выберите "Private" или "Public" в зависимости от ваших предпочтений
5. Установите галочку "Add a README file" (опционально)
6. Выберите .gitignore: "Python"
7. Выберите лицензию (например, "MIT License")
8. Нажмите "Create repository"

## Инициализация локального репозитория

1. Откройте терминал в папке проекта
2. Инициализируйте git репозиторий:
```bash
git init
```

3. Добавьте удаленный репозиторий:
```bash
git remote add origin https://github.com/ваш-username/ваш-репозиторий.git
```

4. Добавьте все файлы:
```bash
git add .
```

5. Сделайте первый коммит:
```bash
git commit -m "Initial commit: Enhanced Truth or Dare Mini-App"
```

6. Запушьте в репозиторий:
```bash
git branch -M main
git push -u origin main
```

## Защита ветки

1. Перейдите в настройки репозитория (Settings → Branches)
2. Установите "main" как default branch
3. Настройте protection rules для ветки main:
   - Require pull request reviews before merging
   - Require status checks to pass before merging
   - Require branches to be up to date before merging

## Установка GitHub Actions (опционально)

Создайте файл `.github/workflows/deploy.yml` для автоматических деплоев:

```yaml
name: Deploy to Railway

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v2
    
    - name: Deploy to Railway
      uses: actions/setup-node@v2
      with:
        node-version: '16'
    - run: npm install -g @railway/cli
    - run: railway up
      env:
        RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Настройка секретов GitHub (для GitHub Actions)

1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте новый secret:
   - Name: `RAILWAY_TOKEN`
   - Value: ваш Railway токен (получить можно через `railway login`)

## Синхронизация с существующим репозиторием

Если вы уже имеете локальный репозиторий:

1. Добавьте удаленный репозиторий:
```bash
git remote add origin https://github.com/ваш-username/ваш-репозиторий.git
```

2. Убедитесь, что у вас есть хотя бы один коммит
3. Запушьте ветку main:
```bash
git branch -M main
git push -u origin main
```

## Защита конфиденциальных данных

Важно: Не пушьте файлы с конфиденциальными данными, такими как:
- `.env` файлы с токенами
- Файлы с паролями
- Конфигурационные файлы с чувствительной информацией

Все эти данные должны быть указаны в `.gitignore` файле.

## Структура репозитория

Ваш репозиторий должен содержать:
- Исходный код приложения
- Файлы конфигурации (кроме содержащих токены)
- Файл README.md с описанием
- Файл requirements.txt с зависимостями
- Файл Procfile для Railway
- Файлы документации
- Файл .gitignore

## Сотрудничество

Для настройки сотрудничества:

1. Перейдите в Settings → Manage access
2. Нажмите "Invite a collaborator"
3. Введите имя пользователя GitHub
4. Выберите уровень доступа (Read, Write, или Admin)