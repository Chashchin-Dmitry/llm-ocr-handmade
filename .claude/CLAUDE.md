# Claude Instructions for llm-ocr-handmade

## Проект

OCR Document Digitization — система для оцифровки документов с использованием локальных AI-моделей.
Извлекает текст из документов (PDF, изображения) и структурирует данные в JSON по пользовательской схеме.

## Стек технологий

- **Backend:** Python 3.11, FastAPI, SQLAlchemy
- **Frontend:** HTML, Tailwind CSS, Alpine.js (SPA)
- **Database:** MySQL 8.0 (на хосте)
- **AI Models:**
  - DeepSeek-OCR 3B — извлечение текста из изображений
  - Qwen2.5-1.5B-Instruct — структуризация в JSON
- **Inference:** vLLM 0.11.2 (OpenAI-compatible API)
- **Container:** Docker Compose

## Структура проекта

```
llm-ocr-handmade/
├── docker-compose.yml      # Все сервисы (vllm-ocr, vllm-qwen, backend)
├── Dockerfile              # Backend image
├── requirements.txt        # Python deps
├── .env.example           # Environment vars
├── backend/
│   ├── main.py            # FastAPI app, endpoints, SSE
│   ├── config.py          # Settings (Pydantic)
│   ├── database.py        # SQLAlchemy setup
│   ├── models.py          # ORM models (Schema, Document, OCRResult, ExtractedData)
│   ├── schemas.py         # Pydantic schemas
│   ├── prompts.py         # AI prompts (OCR + Structuring)
│   └── services/
│       ├── ocr_service.py      # DeepSeek-OCR integration
│       ├── structurizer.py     # Qwen structuring
│       └── file_converter.py   # PDF/DOC to images
├── frontend/
│   └── index.html         # SPA (Alpine.js)
├── uploads/               # Uploaded files
└── .claude/
    ├── CLAUDE.md          # This file
    └── current_stage.md   # Progress tracking
```

## Пайплайн обработки

```
1. Upload (PDF/PNG/JPG) → Document created (status: PENDING)
2. DeepSeek-OCR → Extract text (status: OCR_PROCESSING → OCR_DONE)
3. Qwen → Structure to JSON (status: STRUCTURING → COMPLETED)
```

### DeepSeek-OCR формат

DeepSeek-OCR использует специальный формат промпта:
- `<|grounding|>Convert the document to markdown.` — сохранение layout
- `Free OCR.` — простое извлечение текста

```python
# backend/prompts.py
OCR_USER_PROMPT = "<|grounding|>Convert the document to markdown."
```

### Qwen структуризация

Qwen получает OCR текст и схему колонок, возвращает JSON:

```python
# Пример схемы
columns = [
    {"name": "price", "description": "Цена товара в рублях"},
    {"name": "vendor", "description": "Название продавца"}
]
# Результат: {"price": "399", "vendor": "СимаЛенд"}
```

## API endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/health` | Статус системы и моделей |
| POST | `/api/schemas` | Создать схему |
| GET | `/api/schemas` | Список схем |
| GET | `/api/schemas/{id}` | Схема с колонками |
| DELETE | `/api/schemas/{id}` | Удалить схему |
| POST | `/api/documents/upload/{schema_id}` | Загрузить файлы |
| GET | `/api/documents/{schema_id}` | Документы схемы (с пагинацией) |
| DELETE | `/api/documents/{id}` | Удалить документ |
| POST | `/api/process/{doc_id}` | Обработать документ |
| POST | `/api/process/batch/{schema_id}` | Обработать все pending |
| GET | `/api/process/stream/{schema_id}` | SSE real-time updates |

## Команды разработки

```bash
# Запуск всех сервисов
docker-compose up -d

# Логи моделей
docker-compose logs -f vllm-ocr vllm-qwen

# Логи backend
docker logs ocr-backend -f

# Проверка статуса
curl http://localhost:8001/v1/models  # OCR
curl http://localhost:8002/v1/models  # Qwen
curl http://localhost:8000/api/health # Backend

# GPU мониторинг
nvidia-smi -l 1
```

## Важные файлы для редактирования

1. **backend/prompts.py** — промпты для OCR и структуризации
2. **backend/services/ocr_service.py** — параметры OCR (max_tokens, temperature)
3. **backend/services/structurizer.py** — параметры Qwen (max_tokens, temperature)
4. **docker-compose.yml** — настройки моделей (gpu-memory-utilization, max-model-len)
5. **frontend/index.html** — весь UI

## GPU настройки (RTX 3090 24GB)

| Модель | Параметры | GPU % | max-model-len | VRAM |
|--------|-----------|-------|---------------|------|
| DeepSeek-OCR | 3B | 30% | 4096 | ~8GB |
| Qwen2.5-1.5B | 1.5B | 35% | 16384 | ~9GB |
| **Итого** | | 65% | | ~17GB / 24GB |

## Лимиты токенов

| Сервис | max_tokens | Причина |
|--------|------------|---------|
| OCR | 3500 | Контекст модели 4096, нужен запас для input |
| Qwen | 1024 | Достаточно для JSON ответа |

## Endpoints

| Сервис | Порт | URL |
|--------|------|-----|
| Backend (UI) | 8000 | http://localhost:8000 |
| DeepSeek-OCR | 8001 | http://localhost:8001 |
| Qwen | 8002 | http://localhost:8002 |
| MySQL | 3306 | host.docker.internal:3306 |

## Производительность

- **OCR:** ~21 сек на 3-страничный PDF (7 сек/страница)
- **Структуризация:** ~0.5 сек
- **Общее время:** ~22 сек на документ
- **Confidence:** 75% (на тестовых документах)

## Известные особенности

1. **DeepSeek-OCR grounding** — возвращает координаты элементов в формате `<|ref|>...<|det|>[[x,y,w,h]]`
2. **SSE изоляция** — background tasks и SSE используют отдельные DB сессии для видимости изменений
3. **PDF конвертация** — PDF конвертируется в изображения, каждая страница обрабатывается отдельно
