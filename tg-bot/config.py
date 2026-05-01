"""Загрузка конфигурации из .env."""
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        print(f'ERROR: {key} not set in .env', file=sys.stderr)
        sys.exit(1)
    return value


def _user_ids(raw: str) -> set[int]:
    return {int(x.strip()) for x in raw.split(',') if x.strip()}


@dataclass(frozen=True)
class Config:
    telegram_token: str
    allowed_user_ids: set[int]
    gemini_api_key: str
    gemini_model: str
    sheet_id: str
    service_account_path: str
    product_description: str
    icp_description: str
    language: str
    log_level: str


def load() -> Config:
    return Config(
        telegram_token=_required('TELEGRAM_BOT_TOKEN'),
        allowed_user_ids=_user_ids(_required('ALLOWED_USER_IDS')),
        gemini_api_key=_required('GEMINI_API_KEY'),
        gemini_model=os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp'),
        sheet_id=_required('CRM_SHEET_ID'),
        service_account_path=_required('GOOGLE_SERVICE_ACCOUNT_PATH'),
        product_description=os.getenv('PRODUCT_DESCRIPTION', ''),
        icp_description=os.getenv('ICP_DESCRIPTION', ''),
        language=os.getenv('LANGUAGE', 'ru'),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
    )
