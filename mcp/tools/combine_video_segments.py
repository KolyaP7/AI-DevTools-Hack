"""Макет инструмента для объединения видео сегментов."""

import os
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from tools.utils import ToolResult
from globals import VIDEO_PATH

tracer = trace.get_tracer(__name__)

@mcp.tool(
    name="combine_video_segments",
    description="""🎬 Инструмент для объединения видео сегментов в один ролик.
    """
)
async def combine_video_segments(
    video_files: List[str] = Field(
        ...,
        description="Список видео файлов сегментов"
    ),
    output_file: str = Field(
        ...,
        description="Выходной файл"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Объединяет видео сегменты в один файл.

    Returns:
        ToolResult с output_file
    """
    with tracer.start_as_current_span("combine_video_segments") as span:
        span.set_attribute("video_files", str(video_files))
        span.set_attribute("output_file", output_file)

        await ctx.info("🚀 combine_video_segments started")

        try:
            output_path = os.path.join(VIDEO_PATH, output_file)

            # Mock: create dummy file
            with open(output_path, 'w') as f:
                f.write(f"# Combined video from: {video_files}\n")

            result = {
                "output_file": output_file,
                "status": "combined",
                "segments_count": len(video_files)
            }

            return ToolResult(
                content=[TextContent(type="text", text=f"Videos combined: {output_file}")],
                structured_content=result,
                meta={"video_files": video_files, "output_file": output_file}
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