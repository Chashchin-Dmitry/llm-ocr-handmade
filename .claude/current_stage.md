# OCR Document Digitization - Текущий этап разработки

> Последнее обновление: 2025-12-08

## Цель проекта

Создание MVP системы для оцифровки документов (PNG, PDF, DOC) с использованием:
- **DeepSeek-OCR 3B** — распознавание текста из изображений
- **Qwen2.5-7B** — структуризация данных в JSON по пользовательской схеме

**Ключевая фича**: пользователь сам создаёт колонки и описания к ним, AI использует эти описания для извлечения данных.

---

## Завершённые этапы

### 1. Инфраструктура и Docker
**Файлы:** `docker-compose.yml`, `Dockerfile`, `.env.example`

**Что сделано:**
- Настроен Docker Compose с тремя сервисами:
  - `vllm-ocr` — DeepSeek-OCR на порту 8001
  - `vllm-qwen` — Qwen2.5-7B на порту 8002
  - `mysql` — база данных на порту 3306
- Оптимизировано использование GPU (40% + 50% VRAM для 3090 24GB)

**Почему так:**
- vLLM 0.10.2 официально поддерживает DeepSeek-OCR ([HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-OCR))
- Разделение моделей на разные порты позволяет запускать их одновременно
- MySQL выбран для продакшн-готовности и простоты миграции

---

### 2. Схема базы данных
**Файл:** `backend/models.py`

**Таблицы:**
```
schemas              — Пользовательские схемы (коллекции колонок)
schema_columns       — Колонки с описаниями для AI
documents            — Загруженные документы
ocr_results          — Сырой текст от DeepSeek-OCR
extracted_data       — Структурированный JSON от Qwen
```

**Почему такая структура:**
- `schemas` + `schema_columns` — гибкая система, пользователь сам определяет что извлекать
- Разделение `ocr_results` и `extracted_data` позволяет перезапускать структуризацию без повторного OCR
- Статусы документов (`DocumentStatus`) для отслеживания прогресса в реальном времени

---

### 3. Система промптов
**Файл:** `backend/prompts.py`

**Промпты:**
- `OCR_SYSTEM_PROMPT` — инструкции для DeepSeek-OCR (точность, сохранение структуры)
- `STRUCTURING_SYSTEM_PROMPT` — инструкции для Qwen (только JSON, без выдумок)
- `build_structuring_prompt()` — динамически строит промпт из колонок пользователя

**Почему так:**
- Низкая температура (0.1) для консистентности
- Явные инструкции "не выдумывать" для предотвращения галлюцинаций
- Динамический промпт с описаниями колонок — ключ к гибкости системы

---

### 4. Сервисы для работы с моделями
**Файлы:** `backend/services/ocr_service.py`, `backend/services/structurizer.py`

**Что сделано:**
- `OCRService` — отправка изображений в DeepSeek-OCR через OpenAI-совместимый API vLLM
- `StructurizerService` — структуризация текста через Qwen
- Health-check эндпоинты для мониторинга статуса моделей

**Почему так:**
- vLLM предоставляет OpenAI-совместимый API — простая интеграция
- Base64 кодирование изображений для передачи в API
- Автоматическое извлечение JSON из ответа модели с fallback

---

### 5. FastAPI Backend
**Файл:** `backend/main.py`

**API endpoints:**
- `GET /api/health` — статус системы и моделей
- `POST /api/schemas` — создание схемы
- `GET /api/schemas` — список схем
- `GET /api/schemas/{id}` — получение схемы с колонками
- `DELETE /api/schemas/{id}` — удаление схемы
- `POST /api/schemas/{id}/columns` — добавление колонки
- `DELETE /api/schemas/{id}/columns/{col_id}` — удаление колонки
- `POST /api/documents/upload/{schema_id}` — загрузка файлов
- `GET /api/documents/{schema_id}` — список документов с данными
- `DELETE /api/documents/{id}` — удаление документа
- `POST /api/process/{doc_id}` — обработка одного документа
- `POST /api/process/batch/{schema_id}` — обработка всех pending документов
- `GET /api/process/stream/{schema_id}` — SSE для real-time обновлений

**Почему так:**
- RESTful API для простоты интеграции
- SSE вместо WebSocket — проще, не требует дополнительных библиотек
- Background tasks для асинхронной обработки документов

---

### 6. Frontend
**Файл:** `frontend/index.html`

**Реализовано:**
- Создание схем с колонками через модальное окно
- Добавление/удаление колонок с описаниями для AI
- Drag-and-drop загрузка файлов
- Real-time таблица с результатами через SSE
- Индикаторы статуса моделей (online/offline)
- Просмотр деталей документа (OCR текст + extracted JSON)

**Почему Tailwind + Alpine.js:**
- Без сборки — один HTML файл, простота для статьи
- Tailwind — профессиональный UI через CDN
- Alpine.js — реактивность без тяжёлого фреймворка

---

## Текущий этап

### 7. Тестирование и финализация

**Что осталось:**
- [ ] Запуск и проверка всех компонентов
- [ ] Тест на реальных документах
- [ ] Оптимизация промптов при необходимости

---

## Ссылки на документацию

| Компонент | Документация |
|-----------|-------------|
| DeepSeek-OCR | [HuggingFace Model](https://huggingface.co/deepseek-ai/DeepSeek-OCR) |
| vLLM | [vLLM Docs](https://docs.vllm.ai/) |
| Qwen2.5 | [Qwen GitHub](https://github.com/QwenLM/Qwen2.5) |
| FastAPI | [FastAPI Docs](https://fastapi.tiangolo.com/) |
| SQLAlchemy | [SQLAlchemy Docs](https://docs.sqlalchemy.org/) |
| Tailwind CSS | [Tailwind Docs](https://tailwindcss.com/docs) |
| Alpine.js | [Alpine.js Docs](https://alpinejs.dev/) |

---

## Команды для запуска

```bash
# 1. Копировать .env
cp .env.example .env

# 2. Запустить всё
docker-compose up -d

# 3. Открыть в браузере
http://localhost:8000

# Логи
docker-compose logs -f

# Только MySQL (для разработки без моделей)
docker-compose up -d mysql
uvicorn backend.main:app --reload
```

---

## Архитектура

```
+---------------------------------------------------------------+
|                        Frontend (HTML)                         |
|              Tailwind CSS + Alpine.js + SSE                    |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|                    FastAPI Backend (:8000)                     |
|         /api/schemas, /api/documents, /api/process             |
+---------------------------------------------------------------+
          |                    |                    |
          v                    v                    v
+-----------------+  +-----------------+  +-----------------+
| DeepSeek-OCR    |  |  Qwen2.5-7B     |  |     MySQL       |
| vLLM (:8001)    |  |  vLLM (:8002)   |  |    (:3306)      |
| 3B params       |  |  7B params      |  |                 |
| ~8GB VRAM       |  |  ~14GB VRAM     |  |                 |
+-----------------+  +-----------------+  +-----------------+
```

---

## Поток данных

```
1. Пользователь создаёт схему
   - Указывает название схемы
   - Добавляет колонки с описаниями для AI
   - Пример: "invoice_num" -> "Номер счёта в верхней части документа"

2. Пользователь загружает документы
   - Drag-and-drop или выбор файлов
   - Поддерживаемые форматы: PNG, JPG, PDF, DOC, DOCX
   - Файлы сохраняются в uploads/

3. Запуск обработки
   - Пользователь нажимает "Process All" или "Process" для отдельного документа
   - Backend запускает background task

4. DeepSeek-OCR извлекает текст
   - Изображение кодируется в base64
   - Отправляется в vLLM через OpenAI-совместимый API
   - Результат сохраняется в ocr_results

5. Qwen структурирует данные
   - Получает OCR текст + описания колонок
   - Формирует JSON с извлечёнными данными
   - Результат сохраняется в extracted_data

6. Real-time обновление UI
   - SSE отправляет обновления статуса
   - Таблица обновляется по мере обработки
   - Пользователь видит прогресс в реальном времени
```
