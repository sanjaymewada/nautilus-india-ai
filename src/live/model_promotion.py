"""Guardrails for promoting trained models into live inference."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HORIZONS_MINUTES = (1, 5, 15, 30, 60, 240)


class ModelPromotionGuard:
    """Require minimum validation quality before approving a model artifact."""

    def __init__(
        self,
        model_dir: str | Path = "models/live",
        min_balanced_accuracy: float = 0.52,
        min_validation_rows: int = 100,
    ) -> None:
        if not 0.0 <= min_balanced_accuracy <= 1.0:
            raise ValueError("min_balanced_accuracy must be between 0 and 1")
        if min_validation_rows < 1:
            raise ValueError("min_validation_rows must be positive")

        self.model_dir = Path(model_dir)
        self.min_balanced_accuracy = min_balanced_accuracy
        self.min_validation_rows = min_validation_rows

    def evaluate(self, horizon_minutes: int) -> dict[str, Any]:
        if horizon_minutes not in HORIZONS_MINUTES:
            raise ValueError(f"Unsupported horizon: {horizon_minutes}")

        artifact = self.model_dir / f"model_{horizon_minutes}m.joblib"
        metadata_file = self.model_dir / f"model_{horizon_minutes}m.json"

        if not artifact.is_file() or not metadata_file.is_file():
            return {
                "approved": False,
                "status": "ARTIFACT_OR_METADATA_MISSING",
                "horizon_minutes": horizon_minutes,
            }

        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        metrics = metadata.get("metrics", {})

        balanced_accuracy = metrics.get("balanced_accuracy")
        validation_rows = metrics.get("validation_rows", 0)

        reasons = []
        if metadata.get("horizon_minutes") != horizon_minutes:
            reasons.append("HORIZON_MISMATCH")
        if not isinstance(balanced_accuracy, (int, float)):
            reasons.append("BALANCED_ACCURACY_MISSING")
        elif balanced_accuracy < self.min_balanced_accuracy:
            reasons.append("BALANCED_ACCURACY_TOO_LOW")
        if validation_rows < self.min_validation_rows:
            reasons.append("VALIDATION_SAMPLE_TOO_SMALL")
        if metadata.get("validation_method") != "chronological_holdout":
            reasons.append("UNSUPPORTED_VALIDATION_METHOD")

        return {
            "approved": not reasons,
            "status": "ELIGIBLE_FOR_REVIEW" if not reasons else "REJECTED",
            "horizon_minutes": horizon_minutes,
            "version": metadata.get("version"),
            "reasons": reasons,
            "note": (
                "Eligibility is not proof of profitability. "
                "Review transaction costs, leakage and out-of-sample results."
            ),
        }

    def promote(self, horizon_minutes: int) -> dict[str, Any]:
        """Copy an eligible artifact to a candidate path; do not replace live models."""
        result = self.evaluate(horizon_minutes)
        if not result["approved"]:
            return result

        source = self.model_dir / f"model_{horizon_minutes}m.joblib"
        candidate = self.model_dir / f"candidate_{horizon_minutes}m.joblib"
        shutil.copy2(source, candidate)

        metadata_file = self.model_dir / f"model_{horizon_minutes}m.json"
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        metadata["status"] = "CANDIDATE_REQUIRES_MANUAL_REVIEW"
        metadata["candidate_created_at"] = datetime.now(timezone.utc).isoformat()
        metadata["candidate_artifact"] = str(candidate)

        metadata_file.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        return {
            **result,
            "status": "CANDIDATE_REQUIRES_MANUAL_REVIEW",
            "candidate_artifact": str(candidate),
        }
