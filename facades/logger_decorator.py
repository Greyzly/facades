import sys
import io
import logging
import re
from pathlib import Path
from functools import wraps
from contextlib import redirect_stdout

class LogInterceptor:
    # --- Inner Helper Classes ---
    class _ContextStream(io.StringIO):
        """Intercepts print() output line-by-line."""
        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        def write(self, s):
            if s.strip():  # Skip empty newlines
                self.callback(s.strip())
            return super().write(s)

    class _InterceptorHandler(logging.Handler):
        """Intercepts standard logging module calls."""
        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        def emit(self, record):
            msg = self.format(record)
            self.callback(msg, level_override=record.levelno)

    # --- Main Decorator Logic ---
    def __init__(
        self,
        level: int = logging.INFO,
        fmt: str = "%(asctime)s | %(levelname)-8s | %(message)s",
        handlers: list[logging.Handler] = None,
        log_file: str | Path = None,
        datefmt: str = None,
        style: str = "%",
        **logger_kwargs
    ):
        """
        Self-contained configurable logger decorator.
        """
        self.default_level = level
        self.logger_kwargs = logger_kwargs

        # Build Formatter
        self.formatter = logging.Formatter(fmt=fmt, datefmt=datefmt, style=style)

        # 1. Start with explicitly passed handlers, or default to stdout StreamHandler
        if handlers is not None:
            self.handlers = list(handlers)
        else:
            self.handlers = [logging.StreamHandler(sys.stdout)]

        # 2. Append FileHandler if log_file is specified
        if log_file:
            file_path = Path(log_file)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            self.handlers.append(logging.FileHandler(file_path))

        # Apply formatting to all active handlers
        for h in self.handlers:
            h.setFormatter(self.formatter)

        # Dedicated output logger instance
        self.internal_logger = logging.getLogger("LogInterceptorOutput")
        self.internal_logger.setLevel(logging.DEBUG)  # Let handlers dictate threshold
        self.internal_logger.propagate = False
        self.internal_logger.handlers = self.handlers

        # Patterns for inferring level from print() strings
        self.level_patterns = {
            logging.CRITICAL: re.compile(r'\b(critical|fatal|emergency)\b', re.IGNORECASE),
            logging.ERROR: re.compile(r'\b(error|err|failed|failure|exception)\b', re.IGNORECASE),
            logging.WARNING: re.compile(r'\b(warn|warning|alert)\b', re.IGNORECASE),
            logging.DEBUG: re.compile(r'\b(debug|dbg|trace|verbose)\b', re.IGNORECASE),
        }

    def _infer_level(self, text: str) -> int:
        """Infers logging level based on keywords, falling back to configured default_level."""
        for level, pattern in self.level_patterns.items():
            if pattern.search(text):
                return level
        return self.default_level

    def _process_intercepted_text(self, text: str, level_override: int = None):
        """Emits captured output through internal_logger."""
        level = level_override if level_override is not None else self._infer_level(text)
        self.internal_logger.log(level, text, **self.logger_kwargs)

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Capture print() calls using internal stream
            stream = self._ContextStream(self._process_intercepted_text)
            
            # 2. Intercept native logging calls using internal handler
            interceptor_handler = self._InterceptorHandler(self._process_intercepted_text)
            root_logger = logging.getLogger()
            root_logger.addHandler(interceptor_handler)
            
            try:
                with redirect_stdout(stream):
                    return func(*args, **kwargs)
            finally:
                root_logger.removeHandler(interceptor_handler)

        return wrapper