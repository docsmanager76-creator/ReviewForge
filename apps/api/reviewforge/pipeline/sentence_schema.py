"""Sentence schema written to work/sentences.json. Mirrors the future-field shape of
packages/timeline-schema/src/schema.ts SentenceSchema — Phase 1 only ever populates
id/index/text/startTime/endTime/alignmentConfidence/needsReview; every content-understanding
field (contentType, topic, visualIntent, preferredMediaType, fallbackMediaType,
graphicsRequirement, transitionRequirement) is left as null rather than fabricated, for later
phases to populate."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

SENTENCES_SCHEMA_VERSION = "1.0"


class Sentence(BaseModel):
    id: str
    index: int
    text: str
    startTime: float
    endTime: float

    # Not fabricated in Phase 1 — populated by later phases.
    contentType: Optional[str] = None
    topic: Optional[str] = None
    productSection: Optional[str] = None
    visualIntent: Optional[Dict[str, Any]] = None
    preferredMediaType: Optional[str] = None
    fallbackMediaType: Optional[str] = None
    graphicsRequirement: Optional[Dict[str, Any]] = None
    transitionRequirement: Optional[Dict[str, Any]] = None

    # Phase 1 alignment quality signals.
    alignmentConfidence: float
    needsReview: bool


class SentencesFile(BaseModel):
    version: str = SENTENCES_SCHEMA_VERSION
    sentences: List[Sentence]
