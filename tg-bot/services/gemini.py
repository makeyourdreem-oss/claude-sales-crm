"""Обёртка вокруг Gemini API: транскрипция, анализ, структурирование."""
import json
import logging
from pathlib import Path

import google.generativeai as genai

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """Ты — ассистент по B2B-продажам.

Контекст:
- Продукт: {product}
- ICP: {icp}

На вход тебе придёт расшифровка аудио / текст / описание встречи. Извлеки структуру для CRM.

Верни ТОЛЬКО JSON, без комментариев и markdown-блоков. Структура:

{{
  "type": "lead|company_update|meeting|partner|competitor|task|unknown",
  "company": "Название компании или null если не упомянута",
  "people": [
    {{"name": "ФИО", "role": "должность или null", "contact": "email/телефон или null"}}
  ],
  "history_entry": "Краткая запись для 'Истории взаимодействия' — 1-3 предложения, обязательно укажи дату если она упомянута",
  "next_action": "Что я должен сделать дальше — 1 предложение или null",
  "next_action_date": "YYYY-MM-DD или null",
  "target_sheet": "Лиды|Сделки|Клиенты|Партнёры|Конкуренты|Контакты|Беклог",
  "operation": "create|update",
  "confidence": 0.0..1.0,
  "warnings": ["список неоднозначностей если есть"]
}}

Правила:
- Если компания не упомянута явно — ставь null, target_sheet = "Беклог", type = "task"
- Если компания упомянута но непонятно лид/клиент — ставь "Лиды", confidence < 0.7
- Если переслали переписку — извлекай отправителя в people, контекст в history_entry
- Если в audio мат / личный контекст не про работу — type = "unknown", warnings = ["non-work content"]
- НЕ выдумывай контактные данные. Если не упомянуты — null
"""


class GeminiClient:
    def __init__(self, api_key: str, model_name: str, product: str, icp: str):
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name,
            system_instruction=EXTRACTION_SYSTEM_PROMPT.format(product=product, icp=icp),
            generation_config={'response_mime_type': 'application/json'},
        )

    async def extract_from_text(self, text: str) -> dict:
        """Парсит обычный текст или forwarded message."""
        response = await self._model.generate_content_async(
            f'Содержимое для анализа:\n\n{text}'
        )
        return _parse_json(response.text)

    async def extract_from_audio(self, audio_path: Path) -> dict:
        """Загружает аудио в Gemini, получает структуру (транскрипция внутри)."""
        uploaded = genai.upload_file(str(audio_path))
        response = await self._model.generate_content_async([
            'Расшифруй аудио и проанализируй для CRM. Верни JSON со структурой выше. '
            'В history_entry включи краткую расшифровку.',
            uploaded,
        ])
        try:
            return _parse_json(response.text)
        finally:
            try:
                genai.delete_file(uploaded.name)
            except Exception as e:
                logger.warning('Failed to delete uploaded file: %s', e)

    async def extract_from_document(self, doc_path: Path, doc_text: str | None = None) -> dict:
        """Анализирует документ (PDF/DOCX). Если doc_text передан — использует его, иначе грузит файл целиком."""
        if doc_text:
            return await self.extract_from_text(doc_text)
        uploaded = genai.upload_file(str(doc_path))
        response = await self._model.generate_content_async([
            'Проанализируй документ для CRM. Верни JSON со структурой выше.',
            uploaded,
        ])
        try:
            return _parse_json(response.text)
        finally:
            try:
                genai.delete_file(uploaded.name)
            except Exception as e:
                logger.warning('Failed to delete uploaded file: %s', e)

    async def apply_correction_text(self, original_payload: dict, correction: str) -> dict:
        """Применить текстовую правку к существующему payload."""
        prompt = (
            'Ниже текущий payload для CRM в JSON. Пользователь даёт правку. '
            'Примени правку и верни обновлённый JSON в той же структуре. '
            'Не меняй поля, которых правка не касается.\n\n'
            f'CURRENT PAYLOAD:\n{json.dumps(original_payload, ensure_ascii=False, indent=2)}\n\n'
            f'CORRECTION:\n{correction}'
        )
        response = await self._model.generate_content_async(prompt)
        return _parse_json(response.text)

    async def apply_correction_audio(self, original_payload: dict, audio_path: Path) -> dict:
        """Применить голосовую правку: расшифровать аудио и применить как correction."""
        uploaded = genai.upload_file(str(audio_path))
        prompt = (
            'Ниже текущий payload для CRM в JSON. Пользователь даёт голосовую правку. '
            'Расшифруй аудио, примени правку и верни обновлённый JSON в той же структуре. '
            'Не меняй поля, которых правка не касается.\n\n'
            f'CURRENT PAYLOAD:\n{json.dumps(original_payload, ensure_ascii=False, indent=2)}'
        )
        response = await self._model.generate_content_async([prompt, uploaded])
        try:
            return _parse_json(response.text)
        finally:
            try:
                genai.delete_file(uploaded.name)
            except Exception as e:
                logger.warning('Failed to delete uploaded file: %s', e)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    return json.loads(text.strip())
