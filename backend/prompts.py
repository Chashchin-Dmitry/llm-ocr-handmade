"""
Prompt templates for OCR and data structuring.

Prompts are designed to be clear and produce consistent results.
"""


# ============ OCR Prompt (DeepSeek-OCR) ============
# DeepSeek-OCR uses special prompt format: <image>\n<prompt>
# See: https://github.com/deepseek-ai/DeepSeek-OCR

# For documents with layout preservation (tables, structure)
OCR_PROMPT_DOCUMENT = "<|grounding|>Convert the document to markdown."

# For simple OCR without layout
OCR_PROMPT_SIMPLE = "Free OCR."

# Default prompt for documents
OCR_USER_PROMPT = OCR_PROMPT_DOCUMENT

# Legacy - not used by DeepSeek-OCR
OCR_SYSTEM_PROMPT = ""


# ============ Structuring Prompt (Qwen) ============

STRUCTURING_SYSTEM_PROMPT = """Ты - эксперт по структуризации данных из документов.
Твоя задача - извлечь конкретные данные из текста документа и вернуть их в JSON формате.

Правила:
1. Извлекай ТОЛЬКО те поля, которые указаны в схеме
2. Если поле не найдено в документе - укажи null
3. Сохраняй форматирование дат и чисел как в оригинале
4. Не выдумывай данные - только то, что есть в документе
5. Возвращай ТОЛЬКО валидный JSON, без пояснений"""


def build_structuring_prompt(columns: list[dict], ocr_text: str) -> str:
    """
    Build a prompt for data structuring based on user-defined columns.

    Args:
        columns: List of {"name": "...", "description": "..."} dicts
        ocr_text: Raw OCR text from document

    Returns:
        Formatted prompt for Qwen
    """
    fields_description = "\n".join([
        f'- "{col["name"]}": {col["description"]}'
        for col in columns
    ])

    expected_format = ", ".join([f'"{col["name"]}": значение' for col in columns])

    return f"""Извлеки данные из документа по следующей схеме:

ПОЛЯ ДЛЯ ИЗВЛЕЧЕНИЯ:
{fields_description}

ТЕКСТ ДОКУМЕНТА:
\"\"\"
{ocr_text}
\"\"\"

Верни JSON в точном формате:
{{{expected_format}}}

Если поле не найдено - укажи null.
Возвращай ТОЛЬКО JSON, без дополнительного текста."""


# ============ Validation Prompt ============

VALIDATION_PROMPT = """Проверь извлечённые данные на корректность:
1. Даты в правильном формате?
2. Числа и суммы корректны?
3. Названия организаций полные?
4. Нет ли пропущенных важных данных?

Если всё корректно - верни данные как есть.
Если есть ошибки - исправь и верни исправленную версию."""
