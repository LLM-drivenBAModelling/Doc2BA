from __future__ import annotations

import csv
import json
import re
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Union

from config.ba_config import BusinessArtefactType
from models.schemas import BusinessArtefact, ClassificationResult


NAME_HEADERS = {"name", "artefact", "title", "object", "artefact_name"}
TYPE_HEADERS = {"type", "artefact_type", "artefacttype", "ba_type"}
ID_HEADERS = {"id", "artefact_id"}
CONFIDENCE_HEADERS = {"confidence", "conf"}
SOURCE_SENTENCE_HEADERS = {"source_sentence_ids", "sentence_ids"}
ATTRIBUTES_HEADERS = {"attributes"}
RESERVED_HEADERS = (
    NAME_HEADERS
    | TYPE_HEADERS
    | ID_HEADERS
    | CONFIDENCE_HEADERS
    | SOURCE_SENTENCE_HEADERS
    | ATTRIBUTES_HEADERS
)


class CsvArtefactError(ValueError):
    """Raised when a structured BA CSV cannot be mapped to artefacts."""


def allowed_artefact_type_labels() -> List[str]:
    return [artefact_type.value for artefact_type in BusinessArtefactType]


def resolve_artefact_type(value: str) -> BusinessArtefactType:
    normalized = _normalize_token(value)
    if not normalized:
        raise CsvArtefactError("artefact type is required")
    for artefact_type in BusinessArtefactType:
        if _normalize_token(artefact_type.value) == normalized:
            return artefact_type
        if _normalize_token(artefact_type.name) == normalized:
            return artefact_type
    allowed = ", ".join(allowed_artefact_type_labels())
    raise CsvArtefactError(
        f"unknown artefact type '{value}'. Expected one of: {allowed}"
    )


def classification_from_csv(
    source: Union[str, Path],
    *,
    filename: str = "uploaded.csv",
) -> ClassificationResult:
    """Parse a CSV of business architecture objects into classification data."""
    text, source_name = _read_csv_text(source, filename)
    rows = list(csv.DictReader(StringIO(text)))
    if not rows:
        raise CsvArtefactError("CSV has no data rows")

    fieldnames = [field or "" for field in (rows[0].keys() if rows else [])]
    header_map = _map_headers(fieldnames)
    if "name" not in header_map or "type" not in header_map:
        raise CsvArtefactError(
            "CSV must include 'name' and 'type' columns "
            "(aliases: artefact/title/object and artefact_type/ba_type)"
        )

    artefacts: List[BusinessArtefact] = []
    used_ids: set[str] = set()
    errors: List[str] = []

    for index, row in enumerate(rows, start=2):
        if _row_is_empty(row):
            continue
        try:
            artefact = _artefact_from_row(
                row,
                header_map,
                source_name=source_name,
                used_ids=used_ids,
            )
        except CsvArtefactError as exc:
            errors.append(f"row {index}: {exc}")
            continue
        artefacts.append(artefact)

    if errors:
        raise CsvArtefactError("; ".join(errors))
    if not artefacts:
        raise CsvArtefactError("CSV has no artefact rows")
    return ClassificationResult(artefacts=artefacts)


def _read_csv_text(
    source: Union[str, Path], filename: str
) -> tuple[str, str]:
    if isinstance(source, Path) or (
        isinstance(source, str) and "\n" not in source and Path(source).exists()
    ):
        path = Path(source)
        return path.read_text(encoding="utf-8-sig"), path.name
    return str(source), filename


def _map_headers(fieldnames: Sequence[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for field in fieldnames:
        key = _normalize_header(field)
        if key in NAME_HEADERS and "name" not in mapping:
            mapping["name"] = field
        elif key in TYPE_HEADERS and "type" not in mapping:
            mapping["type"] = field
        elif key in ID_HEADERS and "id" not in mapping:
            mapping["id"] = field
        elif key in CONFIDENCE_HEADERS and "confidence" not in mapping:
            mapping["confidence"] = field
        elif key in SOURCE_SENTENCE_HEADERS and "source_sentence_ids" not in mapping:
            mapping["source_sentence_ids"] = field
        elif key in ATTRIBUTES_HEADERS and "attributes" not in mapping:
            mapping["attributes"] = field
    return mapping


def _artefact_from_row(
    row: Mapping[str, Optional[str]],
    header_map: Mapping[str, str],
    *,
    source_name: str,
    used_ids: set[str],
) -> BusinessArtefact:
    name = _cell(row, header_map["name"])
    type_value = _cell(row, header_map["type"])
    if not name:
        raise CsvArtefactError("name is required")
    artefact_type = resolve_artefact_type(type_value)

    requested_id = _cell(row, header_map["id"]) if "id" in header_map else ""
    artefact_id = _unique_id(requested_id or _kebab_case(name), used_ids)
    used_ids.add(artefact_id)

    confidence = 1.0
    if "confidence" in header_map:
        raw_confidence = _cell(row, header_map["confidence"])
        if raw_confidence:
            try:
                confidence = float(raw_confidence)
            except ValueError as exc:
                raise CsvArtefactError(
                    f"confidence must be a number between 0 and 1, got '{raw_confidence}'"
                ) from exc
            if not 0.0 <= confidence <= 1.0:
                raise CsvArtefactError(
                    f"confidence must be between 0 and 1, got {confidence}"
                )

    source_sentence_ids = None
    if "source_sentence_ids" in header_map:
        raw_ids = _cell(row, header_map["source_sentence_ids"])
        if raw_ids:
            source_sentence_ids = [
                part.strip() for part in re.split(r"[;,]", raw_ids) if part.strip()
            ]

    attributes = _attributes_from_row(row, header_map, source_name)
    return BusinessArtefact(
        id=artefact_id,
        name=name,
        type=artefact_type,
        source_sentence_ids=source_sentence_ids,
        confidence=confidence,
        attributes=attributes,
    )


def _attributes_from_row(
    row: Mapping[str, Optional[str]],
    header_map: Mapping[str, str],
    source_name: str,
) -> Optional[Dict[str, str]]:
    attributes: Dict[str, str] = {"source": source_name}
    if "attributes" in header_map:
        raw = _cell(row, header_map["attributes"])
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CsvArtefactError(
                    f"attributes must be JSON object text, got '{raw}'"
                ) from exc
            if not isinstance(parsed, dict):
                raise CsvArtefactError("attributes JSON must be an object")
            for key, value in parsed.items():
                attributes[str(key)] = "" if value is None else str(value)

    for field, value in row.items():
        if field is None:
            continue
        if _normalize_header(field) in RESERVED_HEADERS:
            continue
        text = (value or "").strip()
        if text:
            attributes[field.strip()] = text

    return attributes or None


def _unique_id(candidate: str, used_ids: Iterable[str]) -> str:
    slug = _kebab_case(candidate)
    if slug not in used_ids:
        return slug
    suffix = 2
    while f"{slug}-{suffix}" in used_ids:
        suffix += 1
    return f"{slug}-{suffix}"


def _kebab_case(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().casefold())
    return slug.strip("-") or "artefact"


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().casefold()).strip("_")


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().casefold())


def _cell(row: Mapping[str, Optional[str]], key: str) -> str:
    return (row.get(key) or "").strip()


def _row_is_empty(row: Mapping[str, Optional[str]]) -> bool:
    return not any((value or "").strip() for value in row.values())
