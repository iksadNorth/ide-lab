"""로깅 설정 모듈."""

from __future__ import annotations

import functools
import logging
import os
from pathlib import Path
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def setup_logging(log_dir: Path | str | None = None) -> logging.Logger:
    """로깅을 설정하고 루트 로거를 반환합니다.

    Args:
        log_dir: 로그 파일을 저장할 디렉토리 경로.
                 None이면 환경 변수 LOG_DIR을 사용하고,
                 환경 변수도 없으면 ./logs/api-server를 사용합니다.

    Returns:
        설정된 루트 로거
    """
    # 로그 디렉토리 설정
    if log_dir is None:
        log_dir = Path(os.getenv("LOG_DIR", "./logs/api-server"))
    else:
        log_dir = Path(log_dir)

    log_dir.mkdir(parents=True, exist_ok=True)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    # 환경 변수로 로그 레벨 설정 (기본값: INFO)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level_value = getattr(logging, log_level, logging.INFO)
    root_logger.setLevel(log_level_value)

    # 파일 핸들러 설정
    log_file = log_dir / "api.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level_value)  # 로거 레벨과 동일하게 설정
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level_value)  # 로거 레벨과 동일하게 설정
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    # 기존 핸들러 제거 (중복 방지)
    root_logger.handlers.clear()

    # 핸들러 추가
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # 특정 라이브러리 로거 레벨 설정 (환경 변수로 제어)
    # 예: LOG_LEVEL_LIBRARIES="selenium:WARNING,urllib3:WARNING,httpcore:WARNING"
    lib_levels = os.getenv("LOG_LEVEL_LIBRARIES", "")
    if lib_levels:
        for lib_config in lib_levels.split(","):
            lib_config = lib_config.strip()
            if ":" in lib_config:
                lib_name, lib_level = lib_config.split(":", 1)
                lib_name = lib_name.strip()
                lib_level = lib_level.strip().upper()
                lib_level_value = getattr(logging, lib_level, logging.WARNING)
                lib_logger = logging.getLogger(lib_name)
                lib_logger.setLevel(lib_level_value)
                # 특정 라이브러리 로거는 핸들러를 추가하지 않음 (루트 로거를 통해 전파)
                lib_logger.propagate = True

    # 기본적으로 자주 사용되는 라이브러리들의 로그 레벨을 WARNING으로 설정
    # (환경 변수로 오버라이드 가능)
    default_lib_levels = {
        "selenium": logging.WARNING,
        "urllib3": logging.WARNING,
        "httpcore": logging.WARNING,
        "httpx": logging.WARNING,
        "asyncio": logging.WARNING,
    }
    
    # 환경 변수로 오버라이드되지 않은 라이브러리만 기본값 적용
    configured_libs = set()
    if lib_levels:
        for lib_config in lib_levels.split(","):
            if ":" in lib_config:
                lib_name = lib_config.split(":", 1)[0].strip()
                configured_libs.add(lib_name)
    
    for lib_name, lib_level_value in default_lib_levels.items():
        if lib_name not in configured_libs:
            lib_logger = logging.getLogger(lib_name)
            lib_logger.setLevel(lib_level_value)
            lib_logger.propagate = True

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """이름으로 로거를 가져옵니다.

    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)

    Returns:
        로거 인스턴스
    """
    return logging.getLogger(name)


def log_method_call(func: F) -> F:
    """메서드/함수 호출과 반환값을 자동으로 로깅하는 데코레이터.
    
    DEBUG 레벨일 때만 작동합니다.
    
    사용 예:
        @log_method_call
        def my_function(arg1, arg2):
            return arg1 + arg2
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # 함수의 모듈명을 사용하여 로거 생성
        logger = logging.getLogger(func.__module__)
        
        # DEBUG 레벨일 때만 로깅
        if not logger.isEnabledFor(logging.DEBUG):
            return func(*args, **kwargs)
        
        # 함수명과 인자 로깅
        func_name = func.__qualname__ if hasattr(func, "__qualname__") else func.__name__
        args_str = ", ".join([repr(arg) for arg in args])
        kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        params_str = ", ".join(filter(None, [args_str, kwargs_str]))
        
        logger.debug(f"→ {func_name}({params_str})")
        
        try:
            result = func(*args, **kwargs)
            # 반환값 로깅 (너무 길면 잘라서 표시)
            result_str = repr(result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "... (truncated)"
            logger.debug(f"← {func_name}() = {result_str}")
            return result
        except Exception as e:
            logger.debug(f"✗ {func_name}() raised {type(e).__name__}: {e}")
            raise
    
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        # 함수의 모듈명을 사용하여 로거 생성
        logger = logging.getLogger(func.__module__)
        
        # DEBUG 레벨일 때만 로깅
        if not logger.isEnabledFor(logging.DEBUG):
            return await func(*args, **kwargs)
        
        # 함수명과 인자 로깅
        func_name = func.__qualname__ if hasattr(func, "__qualname__") else func.__name__
        args_str = ", ".join([repr(arg) for arg in args])
        kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        params_str = ", ".join(filter(None, [args_str, kwargs_str]))
        
        logger.debug(f"→ {func_name}({params_str})")
        
        try:
            result = await func(*args, **kwargs)
            # 반환값 로깅 (너무 길면 잘라서 표시)
            result_str = repr(result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "... (truncated)"
            logger.debug(f"← {func_name}() = {result_str}")
            return result
        except Exception as e:
            logger.debug(f"✗ {func_name}() raised {type(e).__name__}: {e}")
            raise
    
    # async 함수인지 확인
    if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
        return async_wrapper  # type: ignore[return-value]
    return wrapper  # type: ignore[return-value]

