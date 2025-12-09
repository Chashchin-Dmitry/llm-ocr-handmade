# OCR Document Digitization - Текущий этап разработки

> Последнее обновление: 2025-12-09 19:40

---

## ТЕКУЩИЙ СТАТУС: Скачивание vLLM v0.11.2 (~15GB)

### Что нужно сделать завтра

1. **Дождаться загрузки образа vLLM v0.11.2** (~15GB)
   ```bash
   cd "C:/Users/User/Desktop/Projects myself/deepseek ocr project/llm-ocr-handmade"
   docker-compose up -d vllm-ocr vllm-qwen
   ```

2. **Проверить запуск контейнеров**
   ```bash
   docker ps
   docker-compose logs -f vllm-ocr vllm-qwen
   ```

3. **Дождаться загрузки моделей** (при первом запуске)
   - DeepSeek-OCR: ~6GB
   - Qwen2.5-7B: ~15GB
   - Ждать "Application startup complete"

4. **Запустить backend**
   ```bash
   docker-compose up -d backend
   ```

5. **Проверить health**
   ```bash
   curl http://localhost:8001/health  # OCR
   curl http://localhost:8002/health  # Qwen
   curl http://localhost:8000/api/health  # Backend
   ```

6. **Открыть UI**
   - http://localhost:8000

---

## Причинно-следственная связь проблемы с vLLM версиями

### 1. Первая попытка: vLLM v0.10.2
**Что сделали:** Попробовали запустить DeepSeek-OCR с `vllm/vllm-openai:v0.10.2`

**Результат:** ОШИБКА
```
Model architectures ['DeepseekOCRForCausalLM'] are not supported for now.
```

**Причина:** В v0.10.2 архитектура DeepSeek-OCR ещё не была добавлена в upstream vLLM.

---

### 2. Изучили официальную документацию DeepSeek-OCR

**Источник:** https://github.com/deepseek-ai/DeepSeek-OCR

**Нашли ДВА варианта запуска:**

#### Вариант A: Их собственный патченый vLLM 0.8.5
```bash
pip install vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl
```
- Для CUDA 11.8
- Скачивается как .whl файл с GitHub releases
- НЕ Docker образ, а pip пакет
- Требует ручной установки окружения

#### Вариант B: Upstream vLLM v0.11.1+ (nightly)
```bash
# Until v0.11.1 release, you need to install vLLM from nightly build
uv pip install -U vllm --pre --extra-index-url https://wheels.vllm.ai/nightly
```
- Официальная поддержка в upstream vLLM добавлена **2025/10/23**
- Документация говорит нужен v0.11.1+

---

### 3. Проверили Docker Hub

**Доступные образы vLLM:**
- `vllm/vllm-openai:v0.12.0` - ЕСТЬ, но требует CUDA 12.9+
- `vllm/vllm-openai:v0.11.2` - ЕСТЬ, работает с CUDA 12.8
- `vllm/vllm-openai:v0.11.1` - ЕСТЬ, работает с CUDA 12.8
- `vllm/vllm-openai:v0.10.2` - НЕ поддерживает DeepSeek-OCR
- `vllm/vllm-openai:v0.8.5` - БЕЗ патчей DeepSeek

---

### 4. Попытка v0.12.0 - ОШИБКА CUDA

**Ошибка:**
```
nvidia-container-cli: requirement error: unsatisfied condition: cuda>=12.9
please update your driver to a newer version, or use an earlier cuda container
```

**Причина:** vLLM v0.12.0 требует CUDA 12.9+, а у нас CUDA 12.8 (драйвер 571.96)

**Альтернативы:**
1. Обновить драйвер до 576.57+ (для CUDA 12.9)
2. Использовать vLLM v0.11.2 (работает с CUDA 12.8) ✅

---

### 5. РЕШЕНИЕ: vLLM v0.11.2

**docker-compose.yml:**
```yaml
vllm-ocr:
  image: vllm/vllm-openai:v0.11.2  # CUDA 12.8 совместимо!
  command: >
    --model deepseek-ai/DeepSeek-OCR
    --trust-remote-code
    --max-model-len 4096
    --gpu-memory-utilization 0.4
    --enable-prefix-caching false

vllm-qwen:
  image: vllm/vllm-openai:v0.11.2  # CUDA 12.8 совместимо!
  command: >
    --model Qwen/Qwen2.5-7B-Instruct
    --trust-remote-code
    --max-model-len 8192
    --gpu-memory-utilization 0.5
```

**Почему v0.11.2:**
- DeepSeek-OCR поддержка добавлена в v0.11.1 (2025/10/23)
- v0.11.2 работает с CUDA 12.8
- v0.12.0 требует CUDA 12.9+ (несовместимо с текущим драйвером)

---

## Системные требования

### Наша конфигурация
| Параметр | Значение |
|----------|----------|
| GPU | NVIDIA RTX 3090 24GB |
| Driver | 571.96 |
| CUDA | 12.8 |
| Docker | Desktop с WSL2 |
| MySQL | 8.0 (на хосте, порт 3306) |

### GPU распределение
- DeepSeek-OCR: 40% VRAM (~10GB)
- Qwen2.5-7B: 50% VRAM (~12GB)
- Итого: ~22GB из 24GB

---

## Выполненные шаги (2025-12-09)

1. ✅ **SVM Mode включён** - WSL2 теперь работает
2. ✅ **Docker Desktop запущен** - GPU доступна
3. ✅ **GPU проверена** - RTX 3090 видна в контейнерах
4. ✅ **БД создана** - `ocr_documents` в существующем MySQL
5. ✅ **docker-compose обновлён** - использует хостовый MySQL через `host.docker.internal`
6. ✅ **Версия vLLM исследована** - нужен v0.11.2 (не v0.12.0!)
7. ⏳ **Образ v0.11.2 скачивается** - ~15GB

---

## Команды для завтра

```bash
# 1. Перейти в папку проекта
cd "C:/Users/User/Desktop/Projects myself/deepseek ocr project/llm-ocr-handmade"

# 2. Запустить модели (продолжит загрузку образа если не завершена)
docker-compose up -d vllm-ocr vllm-qwen

# 3. Следить за логами
docker-compose logs -f vllm-ocr vllm-qwen

# 4. Когда появится "Application startup complete" - запустить backend
docker-compose up -d backend

# 5. Проверить health
curl http://localhost:8000/api/health

# 6. Открыть в браузере
start http://localhost:8000
```

---

## Важные файлы

| Файл | Описание |
|------|----------|
| `docker-compose.yml` | Конфигурация контейнеров (v0.11.2) |
| `.env` | MySQL пароль и настройки |
| `backend/services/ocr_service.py` | Клиент для DeepSeek-OCR |
| `backend/services/structurizer.py` | Клиент для Qwen |
| `.claude/current_stage.md` | Этот файл |
| `.claude/CLAUDE.md` | Общая документация проекта |

---

## Troubleshooting

### Если CUDA ошибка (cuda>=12.9)
Значит случайно используется v0.12.0. Проверить:
```bash
docker-compose config | grep image
```
Должно быть `vllm/vllm-openai:v0.11.2`

### Если DeepSeek-OCR не поддерживается
Проверить версию vLLM в контейнере:
```bash
docker exec vllm-ocr pip show vllm
```
Должна быть >= 0.11.1

### MySQL пароль со спецсимволами
Пароль `79bFsw!EBqcfK!MY` требует config файл:
```bash
cat > /tmp/mysql_init.cnf << 'EOF'
[client]
user=root
password=79bFsw!EBqcfK!MY
EOF
mysql --defaults-file=/tmp/mysql_init.cnf -e "SHOW DATABASES;"
rm /tmp/mysql_init.cnf
```

---

## Ссылки

- [DeepSeek-OCR GitHub](https://github.com/deepseek-ai/DeepSeek-OCR)
- [vLLM Docker Hub](https://hub.docker.com/r/vllm/vllm-openai/tags)
- [NVIDIA CUDA Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/)
