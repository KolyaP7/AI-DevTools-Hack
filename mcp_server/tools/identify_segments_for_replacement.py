"""Инструмент для идентификации сегментов видео, требующих замены губ, с использованием OpenLLaMA GGUF."""

import os
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_server.mcp_instance import mcp
from mcp_server.tools.utils import ToolResult
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)

# Импорт для работы с LLaMA
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None


@mcp.tool(
    name="identify_segments_for_replacement",
    description="""🧠 Инструмент для анализа текста видео и идентификации сегментов, требующих замены губ, с использованием OpenLLaMA GGUF.
    """
)
async def identify_segments_for_replacement(
    text_segments: List[Dict[str, Any]] = Field(
        ...,
        description="Сегменты текста с временными метками из get_text_from_video"
    ),
    model_path: str = Field(
        "openlm-research/open_llama_3b_v2",  # Пример модели
        description="Путь или имя модели на Hugging Face"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Анализирует сегменты текста из видео и определяет, какие из них требуют замены губ.

    Использует OpenLLaMA GGUF модель для анализа текста и идентификации проблемных сегментов.

    Args:
        text_segments: Список сегментов с 'text', 'start', 'end'
        model_path: Путь к GGUF модели

    Returns:
        ToolResult с сегментами, требующими замены.

    Examples:
        >>> segments = [{"text": "привет", "start": 0, "end": 1}]
        >>> result = await identify_segments_for_replacement(text_segments=segments, ctx)
    """
    with tracer.start_as_current_span("identify_segments_for_replacement") as span:
        span.set_attribute("model_path", model_path)

        await ctx.info("🚀 identify_segments_for_replacement started")
        await ctx.report_progress(progress=0, total=100)

        try:
            if Llama is None:
                raise ImportError("llama-cpp-python not installed")

            # Загрузка модели
            await ctx.report_progress(progress=10, total=100)
            llm = Llama.from_pretrained(
                repo_id=model_path,
                filename="*.gguf",  # Предполагаем GGUF файл
                verbose=False
            )

            # Подготовка текста для анализа
            full_text = " ".join([seg["text"] for seg in text_segments])
            prompt = f"""
            Проанализируй следующий текст из видео и определи сегменты, которые могут требовать замены губ (lip-sync).
            Текст: {full_text}

            Сегменты с временными метками:
            {text_segments}

            Инструкция: Определи, какие сегменты текста могут иметь проблемы с синхронизацией губ.
            Верни список индексов сегментов, которые нужно заменить, и объяснение почему.

            Формат ответа: JSON с полями 'segments_to_replace' (список индексов) и 'reasoning'.
            """

            await ctx.report_progress(progress=50, total=100)

            # Генерация ответа
            output = llm(
                prompt,
                max_tokens=512,
                temperature=0.1,
                stop=["</s>"]
            )

            response_text = output["choices"][0]["text"]

            # Парсинг ответа (предполагаем JSON)
            import json
            try:
                analysis = json.loads(response_text)
                segments_to_replace = analysis.get("segments_to_replace", [])
                reasoning = analysis.get("reasoning", "")
            except json.JSONDecodeError:
                # Если не JSON, взять весь текст
                segments_to_replace = []
                reasoning = response_text

            # Формирование результата
            result_segments = [text_segments[i] for i in segments_to_replace if i < len(text_segments)]

            result = {
                "segments_to_replace": result_segments,
                "reasoning": reasoning,
                "total_segments": len(text_segments),
                "identified_count": len(result_segments)
            }

            await ctx.report_progress(progress=100, total=100)

            return ToolResult(
                content=[TextContent(type="text", text=f"Identified {len(result_segments)} segments for replacement")],
                structured_content=result,
                meta={"model_path": model_path}
            )
        except Exception as e:
            span.set_attribute("error", str(e))
            await ctx.error(f"❌ Ошибка выполнения: {e}")

            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось выполнить операцию: {e}"
                )
            )