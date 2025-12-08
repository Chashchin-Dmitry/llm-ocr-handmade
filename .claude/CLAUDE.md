# Claude Instructions for llm-ocr-handmade

## Проект

OCR Document Digitization — система для оцифровки документов с использованием AI.

## Стек технологий

- **Backend:** Python 3.11, FastAPI, SQLAlchemy
- **Frontend:** HTML, Tailwind CSS, Alpine.js
- **Database:** MySQL 8.0
- **AI Models:** DeepSeek-OCR 3B, Qwen2.5-7B
- **Inference:** vLLM 0.10.2
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
# Запуск для разработки
docker-compose up -d mysql
cd backend && uvicorn main:app --reload

# Полный запуск
docker-compose up -d

# Логи моделей
docker-compose logs -f vllm-ocr vllm-qwen
```

## Важные файлы для редактирования

1. **prompts.py** — изменение поведения AI
2. **models.py** — структура БД
3. **frontend/index.html** — весь UI
4. **docker-compose.yml** — настройки моделей

## GPU настройки (RTX 3090 24GB)

- DeepSeek-OCR: 40% VRAM (~10GB)
- Qwen2.5-7B: 50% VRAM (~12GB)
- Суммарно: ~22GB из 24GB
