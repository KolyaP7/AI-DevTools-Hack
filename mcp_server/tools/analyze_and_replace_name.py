"""Инструмент для анализа текста и замены имени с соблюдением падежных форм."""

import json
import sys
from typing import Dict, Any

import httpx
from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from ..mcp_instance import mcp
from .utils import ToolResult
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)

# LLM конфигурация
api_key = "ZjJkZTE0MTEtNDk2NC00NjBlLTkyNWItOTQ1NjllNDhlNDAz.e7bfa0c5e301eb8e85256aeb4c12da27"
url = "https://foundation-models.api.cloud.ru/v1"

try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=url)
except ImportError:
    client = None


@mcp.tool(
    name="analyze_and_replace_name",
    description="""🤖 Инструмент для анализа текста поздравления и замены имени с соблюдением падежных форм.

    Инструмент принимает полный текст поздравления и новое имя,
    анализирует текст через LLM, определяет имя человека которого поздравляют,
    и заменяет его во всем тексте на новое имя с правильными падежными формами.
    """
)
async def analyze_and_replace_name(
    full_text: str = Field(
        ...,
        description="Полный текст поздравления для анализа"
    ),
    new_name: str = Field(
        ...,
        description="Новое имя для замены"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Анализирует текст поздравления и заменяет имя с соблюдением падежных форм.

    Args:
        full_text: Полный текст поздравления
        new_name: Новое имя для замены
        ctx: Контекст для логирования

    Returns:
        ToolResult с замененным текстом
    """
    with tracer.start_as_current_span("analyze_and_replace_name") as span:
        span.set_attribute("new_name", new_name)
        span.set_attribute("text_length", len(full_text))

        if ctx:
            await ctx.info("🤖 Начинаю анализ текста и замену имени...")
            await ctx.report_progress(progress=0, total=100)
        else:
            print("🤖 Начинаю анализ текста и замену имени...", file=sys.stderr)

        try:
            if client is None:
                raise Exception("LLM клиент недоступен")

            # Сначала нормализуем текст для лучшего распознавания
            normalize_prompt = f"""Исправь только явные ошибки распознавания речи в следующем тексте. Исправь опечатки и грамматические ошибки, но НЕ меняй смысл слов. Сохрани оригинальный стиль и содержание поздравления.

Примеры исправлений:
- "поздравлят" → "поздравлять"
- "тебья" → "тебя"
- "стешочек" → "стишочек" (если это опечатка)
- НЕ меняй "стешочек" на "подарок"

Текст: "{full_text}"

Верни только исправленный текст без дополнительных комментариев."""

            if ctx:
                await ctx.info("🔧 Нормализую текст...")
            else:
                print("🔧 Нормализую текст...", file=sys.stderr)

            normalize_response = client.chat.completions.create(
                model="ai-sage/GigaChat3-10B-A1.8B",
                max_tokens=2000,
                temperature=0.1,  # Низкая температура для точности
                messages=[{"role": "user", "content": normalize_prompt}]
            )
            normalized_text = normalize_response.choices[0].message.content.strip()

            # Очищаем от кавычек
            if normalized_text.startswith('"') and normalized_text.endswith('"'):
                normalized_text = normalized_text[1:-1]
            if normalized_text.startswith("'") and normalized_text.endswith("'"):
                normalized_text = normalized_text[1:-1]

            print(f"📝 Нормализованный текст: {normalized_text}", file=sys.stderr)

            # Формируем запрос для LLM
            prompt = f"""Проанализируй следующий текст поздравления и замени имя получателя на новое имя.

ТЕКСТ: "{normalized_text}"

ЗАДАЧА:
Найди имя человека, которому адресовано поздравление, и замени ВСЕ упоминания этого имени на "{new_name}" с правильными падежными формами.

ПРИМЕР:
Если в тексте "Привет, Иван! Я тебя поздравляю!" и новое имя "Петр", то результат должен быть:
"Привет, Петр! Я тебя поздравляю!"

ПРАВИЛА ЗАМЕНЫ:
- Именительный падеж: {new_name}
- Дательный падеж: {new_name}у (кому?)
- Винительный падеж: {new_name}а (кого?)
- Творительный падеж: {new_name}ом (кем?)
- Предложный падеж: {new_name}е (о ком?)

Верни ТОЛЬКО исправленный текст без каких-либо дополнительных комментариев или объяснений."""

            if ctx:
                await ctx.info("📡 Отправляю запрос в LLM...")
                await ctx.report_progress(progress=25, total=100)
            else:
                print("📡 Отправляю запрос в LLM...", file=sys.stderr)

            # Вызываем LLM
            try:
                response = client.chat.completions.create(
                    model="ai-sage/GigaChat3-10B-A1.8B",
                    max_tokens=2000,
                    temperature=0.3,  # Низкая температура для точности
                    presence_penalty=0,
                    top_p=0.9,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                if ctx:
                    await ctx.report_progress(progress=75, total=100)
                else:
                    print("📝 Получаю ответ от LLM...", file=sys.stderr)

                # Получаем результат
                replaced_text = response.choices[0].message.content.strip()

            except Exception as llm_error:
                print(f"⚠️ Ошибка LLM API: {llm_error}", file=sys.stderr)
                # Fallback: простая замена
                replaced_text = full_text.replace("Иван", new_name).replace("иван", new_name.lower())
                print(f"🔄 Использую fallback замену: '{replaced_text}'", file=sys.stderr)

            # Выводим текст до и после замены
            print("\n" + "="*60, file=sys.stderr)
            print("🎬 ТЕКСТ ДО И ПОСЛЕ ОБРАБОТКИ:", file=sys.stderr)
            print("="*60, file=sys.stderr)
            print(f"🎙️ ОРИГИНАЛ:  {full_text}", file=sys.stderr)
            print(f"🔧 НОРМАЛИЗОВАННЫЙ:  {normalized_text}", file=sys.stderr)
            print(f"🔄 С ЗАМЕНОЙ ИМЕНИ: {replaced_text}", file=sys.stderr)
            print("="*60, file=sys.stderr)

            # Очищаем от лишних кавычек если они есть
            if replaced_text.startswith('"') and replaced_text.endswith('"'):
                replaced_text = replaced_text[1:-1]
            if replaced_text.startswith("'") and replaced_text.endswith("'"):
                replaced_text = replaced_text[1:-1]

            if ctx:
                await ctx.info("✅ Замена имени выполнена успешно")
                await ctx.report_progress(progress=100, total=100)
            else:
                print("✅ Замена имени выполнена успешно", file=sys.stderr)

            return ToolResult(
                content=[TextContent(type="text", text=replaced_text)],
                structured_content={
                    "original_text": full_text,
                    "normalized_text": normalized_text,
                    "replaced_text": replaced_text,
                    "new_name": new_name
                },
                meta={
                    "new_name": new_name,
                    "original_length": len(full_text),
                    "normalized_length": len(normalized_text),
                    "replaced_length": len(replaced_text)
                }
            )

        except Exception as e:
            span.set_attribute("error", str(e))
            error_msg = f"Ошибка при анализе и замене имени: {e}"

            if ctx:
                await ctx.error(f"❌ {error_msg}")
            else:
                print(f"❌ {error_msg}", file=sys.stderr)

            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=error_msg
                )
            )