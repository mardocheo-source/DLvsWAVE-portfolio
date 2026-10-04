"""Display-space collision avoidance for publication chart annotations."""

from __future__ import annotations

from typing import Any

import numpy as np


def _intersection_area(a: Any, b: Any) -> float:
    width = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    height = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    return float(width * height)


def _bbox_overflow_px(bbox: Any, bounds: Any, padding_px: float = 4.0) -> float:
    return float(
        max(0.0, bounds.x0 + padding_px - bbox.x0)
        + max(0.0, bbox.x1 - (bounds.x1 - padding_px))
        + max(0.0, bounds.y0 + padding_px - bbox.y0)
        + max(0.0, bbox.y1 - (bounds.y1 - padding_px))
    )


def densified_display_path(ax: Any, x_values: np.ndarray, y_values: np.ndarray) -> np.ndarray:
    """Sample plotted segments densely and convert them to display coordinates."""
    x_values = np.asarray(x_values, dtype=float)
    y_values = np.asarray(y_values, dtype=float)
    if len(x_values) == 0:
        return np.empty((0, 2), dtype=float)
    if len(x_values) == 1:
        return ax.transData.transform(np.column_stack([x_values, y_values]))
    sampled: list[np.ndarray] = []
    for idx in range(len(x_values) - 1):
        t = np.linspace(0.0, 1.0, 18, endpoint=False)
        sampled.append(
            np.column_stack(
                [
                    x_values[idx] + (x_values[idx + 1] - x_values[idx]) * t,
                    y_values[idx] + (y_values[idx + 1] - y_values[idx]) * t,
                ]
            )
        )
    sampled.append(np.array([[x_values[-1], y_values[-1]]], dtype=float))
    return ax.transData.transform(np.vstack(sampled))


def auto_place_annotation(
    ax: Any,
    text: str,
    xy: tuple[float, float],
    candidates: list[dict[str, Any]],
    occupied_bboxes: list[Any],
    line_points_display: np.ndarray,
    annotation_kwargs: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    """
    Pick the least-colliding candidate using current figure geometry.

    The score accounts for axes overflow, existing text/legend rectangles and
    densely sampled plotted curves. Rotation is selected from the candidates at
    render time and is never tied to a specific date or event.
    """
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    axes_bbox = ax.get_window_extent(renderer)
    best: tuple[float, int, dict[str, Any], dict[str, float]] | None = None

    for priority, candidate in enumerate(candidates):
        trial = ax.annotate(
            text,
            xy=xy,
            xytext=candidate["offset_points"],
            textcoords="offset points",
            rotation=float(candidate.get("rotation", 0.0)),
            ha=str(candidate.get("ha", "center")),
            va=str(candidate.get("va", "bottom")),
            annotation_clip=True,
            clip_on=True,
            **annotation_kwargs,
        )
        fig.canvas.draw()
        patch = trial.get_bbox_patch()
        bbox = patch.get_window_extent(renderer) if patch is not None else trial.get_window_extent(renderer)
        overflow = _bbox_overflow_px(bbox, axes_bbox)
        overlap_area = sum(_intersection_area(bbox, other) for other in occupied_bboxes)
        if line_points_display.size:
            line_hits = int(
                np.count_nonzero(
                    (line_points_display[:, 0] >= bbox.x0 - 2.0)
                    & (line_points_display[:, 0] <= bbox.x1 + 2.0)
                    & (line_points_display[:, 1] >= bbox.y0 - 2.0)
                    & (line_points_display[:, 1] <= bbox.y1 + 2.0)
                )
            )
        else:
            line_hits = 0
        displacement = float(np.hypot(*candidate["offset_points"]))
        score = overflow * 1_000_000.0 + overlap_area * 100.0 + line_hits * 350.0 + displacement + priority
        details = {
            "overflow_px": float(overflow),
            "overlap_area_px2": float(overlap_area),
            "line_sample_hits": float(line_hits),
        }
        trial.remove()
        if best is None or score < best[0]:
            best = (score, priority, candidate, details)

    if best is None:
        raise RuntimeError("No annotation placement candidates were supplied")

    score, _, selected, details = best
    annotation = ax.annotate(
        text,
        xy=xy,
        xytext=selected["offset_points"],
        textcoords="offset points",
        rotation=float(selected.get("rotation", 0.0)),
        ha=str(selected.get("ha", "center")),
        va=str(selected.get("va", "bottom")),
        annotation_clip=True,
        clip_on=True,
        **annotation_kwargs,
    )
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    patch = annotation.get_bbox_patch()
    bbox = patch.get_window_extent(renderer) if patch is not None else annotation.get_window_extent(renderer)
    occupied_bboxes.append(bbox)
    bbox_axes = bbox.transformed(ax.transAxes.inverted())
    audit = {
        "text": text,
        "anchor": [float(xy[0]), float(xy[1])],
        "rotation_degrees": float(selected.get("rotation", 0.0)),
        "offset_points": [float(v) for v in selected["offset_points"]],
        "bbox_axes_fraction": [float(bbox_axes.x0), float(bbox_axes.y0), float(bbox_axes.x1), float(bbox_axes.y1)],
        "within_axes": bool(details["overflow_px"] <= 0.01),
        "collision_score": float(score),
        **details,
    }
    return annotation, audit
