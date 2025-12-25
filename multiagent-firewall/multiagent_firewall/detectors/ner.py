from __future__ import annotations

from functools import lru_cache
from typing import Mapping, Sequence

from ..types import FieldList


class GlinerNERDetector:
    """Run GLiNER with configured labels and map them to canonical fields."""

    def __init__(
        self,
        *,
        model: str,
        labels: Sequence[str],
        label_map: Mapping[str, str] | None = None,
        min_score: float = 0.0,
    ) -> None:
        if not labels:
            raise ValueError("NER labels must not be empty.")
        self._model_name = model
        self._labels = [label.strip() for label in labels if label and label.strip()]
        self._label_map = {
            key.strip().upper(): value.strip().upper()
            for key, value in (label_map or {}).items()
        }
        self._min_score = min_score

    def detect(self, text: str) -> FieldList:
        if not text:
            return []
        gliner = _load_gliner(self._model_name)
        labels = list(self._labels)
        entities = gliner.predict_entities(text, labels)
        findings: FieldList = []
        for entity in entities or []:
            if not isinstance(entity, dict):
                continue
            label = entity.get("label")
            value = entity.get("text")
            if not label or not value:
                continue
            score = entity.get("score")
            if isinstance(score, (int, float)) and score < self._min_score:
                continue
            field = self._map_label(str(label))
            findings.append(
                {
                    "field": field,
                    "value": str(value),
                    "sources": ["ner_gliner"],
                    "score": score,
                }
            )
        return findings

    def _map_label(self, label: str) -> str:
        normalized = label.strip().upper()
        return self._label_map.get(normalized, normalized)


@lru_cache(maxsize=2)
def _load_gliner(model_name: str):
    try:
        from gliner import GLiNER
    except Exception as exc:
        raise RuntimeError(
            "GLiNER is not installed. Install it as an extra using uv sync --extra ner"
        ) from exc

    model = GLiNER.from_pretrained(model_name)
    return model


__all__ = ["GlinerNERDetector"]
