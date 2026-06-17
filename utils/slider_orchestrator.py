"""滑块验证编排与严格结果判定工具。

调用现有 XianyuSliderStealth 后，必须拿到 x5/x5sec 相关 Cookie 才认为
平台真正放行，避免“视觉通过但未下发 x5sec”被误当成功而导致 token
刷新死循环；同时提供可选 DrissionPage 兜底入口。
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Callable, Dict, Mapping, Optional, Tuple, Union


DEFAULT_SLIDER_ENGINE = "playwright"
DRISSIONPAGE_ENGINE = "drissionpage"
_COOKIE_ATTR_NAMES = {"path", "domain", "expires", "max-age", "secure", "httponly", "samesite"}


@dataclass(frozen=True)
class SliderVerificationResult:
    """标准化滑块验证结果。"""

    success: bool
    cookies: Optional[Dict[str, Any]]
    engine: str
    x5_cookies: Dict[str, Any]
    message: str

    def as_legacy_tuple(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """兼容旧调用方的 ``(success, cookies)`` 返回格式。"""
        return self.success, self.cookies


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def parse_cookie_string(cookie_text: Optional[str]) -> Dict[str, str]:
    """解析 Cookie / Set-Cookie 字符串为字典。"""
    result: Dict[str, str] = {}
    if not cookie_text:
        return result

    # Set-Cookie 可能用逗号分隔多个 cookie；这里做保守解析，只取 name=value 片段。
    normalized_text = str(cookie_text).replace("\ufeff", "").replace(", ", "; ")
    for part in normalized_text.split(";"):
        item = part.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        if key and key.lower() not in _COOKIE_ATTR_NAMES:
            result[key] = value.strip()
    return result


def extract_x5_cookies(cookies: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """提取 x5/x5sec 相关 Cookie。"""
    if not isinstance(cookies, Mapping):
        return {}

    result: Dict[str, Any] = {}
    for name, value in cookies.items():
        name_lower = str(name or "").lower()
        if name_lower.startswith("x5") or "x5sec" in name_lower:
            result[str(name)] = value
    return result


def has_x5_cookie(cookies: Optional[Mapping[str, Any]]) -> bool:
    """判断浏览器返回 Cookie 中是否包含真正放行用的 x5/x5sec 票据。"""
    return bool(extract_x5_cookies(cookies))


def validate_slider_result(
    success: bool,
    cookies: Optional[Union[Mapping[str, Any], str]],
    *,
    engine: Optional[str] = DEFAULT_SLIDER_ENGINE,
) -> SliderVerificationResult:
    """严格判定滑块结果。

    旧逻辑只要页面视觉上通过且返回了任意 Cookie 就可能进入成功分支。
    闲鱼/阿里风控下，视觉通过但没有下发 x5sec 时，后续 token 接口仍会
    继续返回验证要求。因此这里强制要求 x5/x5sec 相关 Cookie。
    """
    normalized_engine = str(engine or DEFAULT_SLIDER_ENGINE).strip() or DEFAULT_SLIDER_ENGINE
    if isinstance(cookies, str):
        normalized_cookies = parse_cookie_string(cookies)
    else:
        normalized_cookies = dict(cookies or {}) if isinstance(cookies, Mapping) else None
    x5_cookies = extract_x5_cookies(normalized_cookies)

    if not success:
        return SliderVerificationResult(
            success=False,
            cookies=None,
            engine=normalized_engine,
            x5_cookies={},
            message="滑块验证失败",
        )

    if not normalized_cookies:
        return SliderVerificationResult(
            success=False,
            cookies=None,
            engine=normalized_engine,
            x5_cookies={},
            message="滑块视觉通过但未返回 Cookie，平台可能未真正放行",
        )

    if not x5_cookies:
        return SliderVerificationResult(
            success=False,
            cookies=normalized_cookies,
            engine=normalized_engine,
            x5_cookies={},
            message=(
                "滑块视觉通过但未获取到 x5sec Cookie，判定为失败；"
                "常见原因是浏览器环境/IP 仍被风控拦截"
            ),
        )

    return SliderVerificationResult(
        success=True,
        cookies=normalized_cookies,
        engine=normalized_engine,
        x5_cookies=x5_cookies,
        message="滑块验证成功并获取到 x5sec Cookie",
    )


def _run_drissionpage_fallback(
    url: str,
    *,
    user_id: str,
    existing_cookies_str: str = "",
    headless: bool = True,
    max_retries: int = 3,
    handler_factory: Optional[Callable[..., Any]] = None,
) -> SliderVerificationResult:
    """运行 DrissionPage 兜底引擎并返回严格判定结果。"""
    try:
        if handler_factory is None:
            from utils.refresh_util import DrissionHandler
            handler_factory = DrissionHandler
        handler = handler_factory(
            max_retries=max_retries,
            is_headless=headless,
            maximize_window=not headless,
            show_mouse_trace=False,
        )
        raw_cookies = handler.get_cookies(url, existing_cookies_str=existing_cookies_str, cookie_id=user_id)
        return validate_slider_result(bool(raw_cookies), raw_cookies, engine=DRISSIONPAGE_ENGINE)
    except Exception as exc:
        return SliderVerificationResult(
            success=False,
            cookies=None,
            engine=DRISSIONPAGE_ENGINE,
            x5_cookies={},
            message=f"DrissionPage兜底引擎执行失败: {exc}",
        )


def run_slider_strict(
    slider: Any,
    url: str,
    *,
    engine: Optional[str] = DEFAULT_SLIDER_ENGINE,
    **kwargs: Any,
) -> SliderVerificationResult:
    """调用同步 slider.run，并进行严格 x5sec 判定。"""
    success, cookies = slider.run(url, **kwargs)
    return validate_slider_result(success, cookies, engine=engine)


def run_slider_with_fallback(
    slider: Any,
    url: str,
    *,
    engine: Optional[str] = DEFAULT_SLIDER_ENGINE,
    fallback_enabled: Optional[bool] = None,
    fallback_headless: Optional[bool] = None,
    fallback_max_retries: int = 3,
    handler_factory: Optional[Callable[..., Any]] = None,
    **kwargs: Any,
) -> SliderVerificationResult:
    """先运行现有 Playwright 滑块，失败时可用 DrissionPage 兜底。"""
    primary_result = run_slider_strict(slider, url, engine=engine, **kwargs)
    if primary_result.success:
        return primary_result

    enabled = _env_bool("XY_SLIDER_DRISSION_FALLBACK", True) if fallback_enabled is None else bool(fallback_enabled)
    if not enabled:
        return primary_result

    user_id = str(getattr(slider, "user_id", None) or getattr(slider, "pure_user_id", None) or "unknown")
    existing_cookies_str = str(getattr(slider, "initial_cookies", "") or "")
    headless = bool(getattr(slider, "headless", True)) if fallback_headless is None else bool(fallback_headless)
    fallback_result = _run_drissionpage_fallback(
        url,
        user_id=user_id,
        existing_cookies_str=existing_cookies_str,
        headless=headless,
        max_retries=fallback_max_retries,
        handler_factory=handler_factory,
    )
    return fallback_result if fallback_result.success else primary_result


async def run_slider_async_strict(
    slider: Any,
    url: str,
    *,
    engine: Optional[str] = DEFAULT_SLIDER_ENGINE,
    **kwargs: Any,
) -> SliderVerificationResult:
    """调用异步 slider.async_run，并进行严格 x5sec 判定。"""
    success, cookies = await slider.async_run(url, **kwargs)
    return validate_slider_result(success, cookies, engine=engine)


async def run_slider_async_with_fallback(
    slider: Any,
    url: str,
    *,
    engine: Optional[str] = DEFAULT_SLIDER_ENGINE,
    fallback_enabled: Optional[bool] = None,
    fallback_headless: Optional[bool] = None,
    fallback_max_retries: int = 3,
    handler_factory: Optional[Callable[..., Any]] = None,
    **kwargs: Any,
) -> SliderVerificationResult:
    """异步版本：Playwright 严格判定失败后可运行 DrissionPage 兜底。"""
    primary_result = await run_slider_async_strict(slider, url, engine=engine, **kwargs)
    if primary_result.success:
        return primary_result

    enabled = _env_bool("XY_SLIDER_DRISSION_FALLBACK", True) if fallback_enabled is None else bool(fallback_enabled)
    if not enabled:
        return primary_result

    import asyncio

    user_id = str(getattr(slider, "user_id", None) or getattr(slider, "pure_user_id", None) or "unknown")
    existing_cookies_str = str(getattr(slider, "initial_cookies", "") or "")
    headless = bool(getattr(slider, "headless", True)) if fallback_headless is None else bool(fallback_headless)
    fallback_result = await asyncio.to_thread(
        _run_drissionpage_fallback,
        url,
        user_id=user_id,
        existing_cookies_str=existing_cookies_str,
        headless=headless,
        max_retries=fallback_max_retries,
        handler_factory=handler_factory,
    )
    return fallback_result if fallback_result.success else primary_result
