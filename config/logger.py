import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_ai import AgentRunResult

_LOG_FILE = Path(__file__).resolve().parents[1] / "server.log"
_FILE_FORMATTER = logging.Formatter(
    fmt="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_CONSOLE_FORMATTER = logging.Formatter(
    fmt="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
    datefmt="%H:%M:%S",
)


def _file_handler() -> logging.FileHandler:
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_FILE_FORMATTER)
    return fh


def _console_handler() -> logging.StreamHandler:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(_CONSOLE_FORMATTER)
    return ch


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_file_handler())
        logger.addHandler(_console_handler())
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger


def log_agent_run(logger: logging.Logger, result: "AgentRunResult") -> None:
    from pydantic_ai.messages import (
        ModelRequest, ModelResponse,
        TextPart, ToolCallPart, ToolReturnPart, UserPromptPart,
    )
    for msg in result.all_messages():
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart):
                    logger.debug("[model-request] prompt: %s", part.content)
                elif isinstance(part, ToolReturnPart):
                    logger.debug(
                        "[tool-return] %s -> %s",
                        part.tool_name, part.content,
                    )
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart):
                    logger.debug("[model-response] text: %s", part.content)
                elif isinstance(part, ToolCallPart):
                    logger.debug(
                        "[model-response] tool-call: %s  args: %s",
                        part.tool_name, part.args,
                    )
