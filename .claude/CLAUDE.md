# Claude Instructions for llm-ocr-handmade

## Проект

OCR Document Digitization — система для оцифровки документов с использованием AI.

## Стек технологий

- **Backend:** Python 3.11, FastAPI, SQLAlchemy
- **Frontend:** HTML, Tailwind CSS, Alpine.js
- **Database:** MySQL 8.0
- **AI Models:** DeepSeek-OCR 3B, Qwen2.5-1.5B-Instruct
- **Inference:** vLLM 0.11.2
- **Container:** Docker Compose

## Структура проекта

```
llm-ocr-handmade/
├── docker-compose.yml      # Все сервисы
├── Dockerfile              # Backend image
├── requirements.txt        # Python deps
├── .env.example           # Environment vars
├── backend/
│   ├── main.py            # FastAPI app
│   ├── config.py          # Settings
│   ├── database.py        # SQLAlchemy setup
│   ├── models.py          # ORM models
│   ├── schemas.py         # Pydantic schemas
│   ├── prompts.py         # AI prompts
│   └── services/
│       ├── ocr_service.py      # DeepSeek-OCR
│       └── structurizer.py     # Qwen structuring
├── frontend/
│   └── index.html         # SPA
├── uploads/               # Uploaded files
└── .claude/
    ├── CLAUDE.md          # This file
    └── current_stage.md   # Progress tracking
```

## Ключевые концепции

### Пользовательские схемы
Пользователи создают свои колонки с описаниями. AI использует описания для понимания что извлекать.

```python
# Пример колонки
{
    "name": "invoice_num",
    "description": "Номер счёта или накладной"
}
```

### Пайплайн обработки
1. Загрузка документа (PNG/PDF/DOC)
2. DeepSeek-OCR извлекает текст
3. Qwen структурирует в JSON по схеме
4. Результат сохраняется в БД

### API endpoints
- `GET /api/health` — статус системы и моделей
- `POST /api/schemas` — создать схему
- `GET /api/schemas` — список схем
- `POST /api/documents/upload` — загрузить файлы
- `GET /api/documents/{schema_id}` — документы схемы
- `GET /api/process/stream/{doc_id}` — SSE прогресс

## Команды разработки

```bash
# Запуск всех сервисов
docker-compose up -d

# Логи моделей
docker-compose logs -f vllm-ocr vllm-qwen

# Проверка статуса
curl http://localhost:8001/v1/models  # OCR
curl http://localhost:8002/v1/models  # Qwen
curl http://localhost:8000/api/health # Backend
```

## Важные файлы для редактирования

1. **prompts.py** — изменение поведения AI
2. **models.py** — структура БД
3. **frontend/index.html** — весь UI
4. **docker-compose.yml** — настройки моделей

## GPU настройки (RTX 3090 24GB)

| Модель | Параметры | GPU % | VRAM |
|--------|-----------|-------|------|
| DeepSeek-OCR | 3B | 40% | ~10GB |
| Qwen2.5-1.5B | 1.5B | 20% | ~5GB |
| **Итого** | | | ~17GB / 24GB |

**Требования:**
- NVIDIA Driver 576+ (CUDA 12.9)
- vLLM 0.11.2 (поддержка DeepSeek-OCR добавлена в v0.11.1)

## Endpoints

| Сервис | Порт | URL |
|--------|------|-----|
| Backend (UI) | 8000 | http://localhost:8000 |
| DeepSeek-OCR | 8001 | http://localhost:8001 |
| Qwen | 8002 | http://localhost:8002 |
