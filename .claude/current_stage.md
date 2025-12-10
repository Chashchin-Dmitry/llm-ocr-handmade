# OCR Document Digitization - Текущий этап

> Последнее обновление: 2025-12-10 17:10

---

## СТАТУС: MVP ЗАВЕРШЁН

Система полностью работает. OCR пайплайн протестирован и функционирует.

---

## Выполнено

### Инфраструктура
- NVIDIA Driver 576.88 (CUDA 12.9)
- vLLM v0.11.2 (поддержка DeepSeek-OCR)
- Docker Compose с 3 сервисами
- MySQL 8.0 на хосте

### AI модели
- DeepSeek-OCR 3B (порт 8001, 30% GPU)
- Qwen2.5-1.5B-Instruct (порт 8002, 35% GPU)
- Обе модели работают параллельно (~17GB / 24GB)

### Backend
- FastAPI с async обработкой
- Background tasks для OCR
- SSE для real-time updates
- PDF/DOC конвертация в изображения

### Frontend
- SPA на Alpine.js
- Создание схем и колонок
- Загрузка документов
- Просмотр результатов

---

## Производительность

| Метрика | Значение |
|---------|----------|
| OCR (3 страницы PDF) | ~21 сек |
| Структуризация | ~0.5 сек |
| Общее время | ~22 сек |
| Confidence | 75% |

---

## Решённые проблемы

| Проблема | Решение |
|----------|---------|
| DeepSeek-OCR 400 Bad Request | Специальный формат промпта `<image>\n<prompt>` |
| max_tokens слишком большой | OCR: 3500, Qwen: 1024 |
| Qwen 7B не влезает | Использовали 1.5B-Instruct |
| Qwen контекст 2048 мал | Увеличили до 16384 |
| SSE не видит изменения | Изолированные DB сессии + rollback() |

---

## Конфигурация

```yaml
# docker-compose.yml
vllm-ocr:
  --model deepseek-ai/DeepSeek-OCR
  --max-model-len 4096
  --gpu-memory-utilization 0.30

vllm-qwen:
  --model Qwen/Qwen2.5-1.5B-Instruct
  --max-model-len 16384
  --gpu-memory-utilization 0.35
```

---

## Endpoints

| Сервис | URL | Статус |
|--------|-----|--------|
| Frontend | http://localhost:8000 | OK |
| DeepSeek-OCR | http://localhost:8001 | OK |
| Qwen | http://localhost:8002 | OK |
| Health | http://localhost:8000/api/health | OK |

---

## Мониторинг

```bash
# Статус контейнеров
docker ps

# Логи backend
docker logs ocr-backend -f

# Логи моделей
docker logs vllm-ocr --tail 20
docker logs vllm-qwen --tail 20

# GPU
nvidia-smi
```

---

## Возможные улучшения (TODO)

- [ ] Фильтрация grounding токенов из OCR output
- [ ] Batch processing с очередью
- [ ] Экспорт в Excel/CSV
- [ ] Валидация извлечённых данных
- [ ] Более умная модель (Qwen 7B/14B на большем GPU)
