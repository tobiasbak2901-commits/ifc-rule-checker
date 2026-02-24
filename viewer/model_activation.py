from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, Optional

from viewer.model_payload import ModelPayload


@dataclass(frozen=True)
class ActivationResult:
    viewerModelLoaded: bool
    elementsParsed: int
    meshesRendered: int
    warning: Optional[str]
    autoFitCalls: int


@dataclass(frozen=True)
class ActivationStoreSnapshot:
    activationCount: int
    lastActivationSourceTag: str
    activationToken: int
    isActivating: bool


class ModelActivationStore:
    """
    Single source of truth for model activation.
    Calls are serialized. If activateModel is invoked while activating, only the
    latest payload is kept (last-write-wins) and runs next.
    """

    def __init__(self, activation_callback: Callable[..., Any], *, debounce_ms: int = 50):
        self._activation_callback = activation_callback
        self._queued: Optional[tuple[ModelPayload, str, Dict[str, Any]]] = None
        self._debounce_ms = max(0, int(debounce_ms))
        self._last_completed_payload_id: Optional[int] = None
        self._last_completed_at: float = 0.0
        self._active_payload_id: Optional[int] = None
        self.activationCount = 0
        self.lastActivationSourceTag = ""
        self.activationToken = 0
        self.isActivating = False

    def reset(self) -> None:
        self._queued = None
        self._last_completed_payload_id = None
        self._last_completed_at = 0.0
        self._active_payload_id = None
        self.activationCount = 0
        self.lastActivationSourceTag = ""
        self.activationToken = 0
        self.isActivating = False

    def snapshot(self) -> ActivationStoreSnapshot:
        return ActivationStoreSnapshot(
            activationCount=int(self.activationCount),
            lastActivationSourceTag=str(self.lastActivationSourceTag or ""),
            activationToken=int(self.activationToken),
            isActivating=bool(self.isActivating),
        )

    def should_cancel(self, token: int) -> bool:
        return bool(
            self.isActivating
            and self._queued is not None
            and int(token) == int(self.activationToken)
        )

    def activateModel(
        self,
        modelPayload: ModelPayload,
        sourceTag: str,
        **kwargs: Any,
    ) -> int:
        if modelPayload is None:
            return self.activationToken
        now = time.monotonic()
        payload_id = id(modelPayload)
        if (
            not self.isActivating
            and self._last_completed_payload_id == payload_id
            and ((now - self._last_completed_at) * 1000.0) <= float(self._debounce_ms)
        ):
            return self.activationToken
        if self.isActivating and self._active_payload_id == payload_id:
            return self.activationToken
        self._queued = (modelPayload, str(sourceTag or "unknown"), dict(kwargs or {}))
        if self.isActivating:
            return self.activationToken

        while self._queued is not None:
            payload, source_tag, callback_kwargs = self._queued
            active_payload_id = id(payload)
            self._queued = None
            self.isActivating = True
            self._active_payload_id = active_payload_id
            self.activationToken += 1
            token = int(self.activationToken)
            self.activationCount += 1
            self.lastActivationSourceTag = source_tag
            try:
                self._activation_callback(
                    payload,
                    sourceTag=source_tag,
                    token=token,
                    **callback_kwargs,
                )
            finally:
                self.isActivating = False
                self._active_payload_id = None
                self._last_completed_payload_id = active_payload_id
                self._last_completed_at = time.monotonic()
        return self.activationToken


def activate_model_payload(
    model_payload: ModelPayload,
    *,
    attach_meshes: Callable[[ModelPayload], int],
    auto_fit_to_bbox: Callable[[object], None],
) -> ActivationResult:
    elements_parsed = int(len(model_payload.elements))
    meshes_rendered = int(max(0, int(attach_meshes(model_payload))))
    viewer_loaded = elements_parsed > 0
    warning: Optional[str] = None

    if viewer_loaded and meshes_rendered == 0:
        warning = "IFC loaded, but no triangulated geometry produced (0 meshes)."

    auto_fit_calls = 0
    if meshes_rendered > 0 and model_payload.bboxWorld is not None:
        auto_fit_to_bbox(model_payload.bboxWorld)
        auto_fit_calls = 1

    return ActivationResult(
        viewerModelLoaded=viewer_loaded,
        elementsParsed=elements_parsed,
        meshesRendered=meshes_rendered,
        warning=warning,
        autoFitCalls=auto_fit_calls,
    )
