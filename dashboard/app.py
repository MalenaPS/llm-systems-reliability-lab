from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

RUNS_DIR = Path("runs")


# --------------------------------------------------
# DATA LOADING
# --------------------------------------------------


def parse_run_timestamp(run_name: str) -> datetime:
    """
    Expected run_id prefix format: YYYYMMDD-HHMMSS-...
    Falls back to datetime.min if parsing fails.
    """
    match = re.match(r"^(\d{8})-(\d{6})", run_name)
    if not match:
        return datetime.min
    try:
        return datetime.strptime(f"{match.group(1)}-{match.group(2)}", "%Y%m%d-%H%M%S")
    except ValueError:
        return datetime.min


def list_runs() -> list[Path]:
    if not RUNS_DIR.exists():
        return []
    return sorted(
        [p for p in RUNS_DIR.iterdir() if p.is_dir()],
        key=lambda x: parse_run_timestamp(x.name),
        reverse=True,
    )


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in lines if x.strip()]


# --------------------------------------------------
# RUN INTROSPECTION
# --------------------------------------------------


def detect_run_kind(run_dir: Path) -> str:
    has_metrics = (run_dir / "metrics.json").exists()
    has_output = (run_dir / "output.json").exists()
    has_drift = (run_dir / "drift_report_local.json").exists() or (
        run_dir / "drift_report.json"
    ).exists()
    has_redteam = (run_dir / "redteam_report.json").exists() or (
        run_dir / "attack_report.json"
    ).exists()
    has_reliability = (run_dir / "reliability_report.json").exists()

    if has_drift:
        return "drift"
    if has_redteam:
        return "redteam"
    if has_reliability:
        return "reliability"
    if has_output and has_metrics:
        return "case_run"
    return "generic"


def available_files_by_group(run_dir: Path) -> dict[str, list[str]]:
    groups = {
        "Core": [
            "metrics.json",
            "step_metrics.json",
            "events.jsonl",
            "output.json",
            "run_manifest.json",
        ],
        "Drift": [
            "drift_report.json",
            "drift_report_local.json",
            "drift_report.md",
            "drift_report_local.md",
        ],
        "Red Team": [
            "attack_report.json",
            "redteam_report.json",
        ],
        "Reliability": [
            "reliability_report.json",
        ],
        "Eval": [
            "llm_grades.json",
            "leaderboard.md",
        ],
    }
    return {
        group: [name for name in names if (run_dir / name).exists()]
        for group, names in groups.items()
    }


def format_run_label(run_dir: Path) -> str:
    kind = detect_run_kind(run_dir)
    return f"{run_dir.name} · {kind}"


def latest_run_by_type(runs: list[Path], run_kind: str) -> Path | None:
    for run in runs:
        if detect_run_kind(run) == run_kind:
            return run
    return None


def count_runs_by_type(runs: list[Path]) -> dict[str, int]:
    counts = {
        "case_run": 0,
        "drift": 0,
        "redteam": 0,
        "reliability": 0,
        "generic": 0,
    }
    for run in runs:
        counts[detect_run_kind(run)] += 1
    return counts


# --------------------------------------------------
# UI HELPERS
# --------------------------------------------------


def normalize_metric_display(value: Any):
    if value is None:
        return "—"
    if isinstance(value, float):
        return round(value, 3)
    return value


def metric_status(key: str, value: Any) -> tuple[str, str]:
    """
    Returns (level, message) where level in {"success", "warning", "error", "info"}.
    """
    if value in (None, "—"):
        return "info", "Not available"

    if not isinstance(value, (int, float)):
        return "info", "Informational metric"

    high_is_good = {
        "success_rate",
        "schema_compliance_rate",
        "tool_success_rate",
        "citations_valid_rate",
        "recovery_rate",
        "answer_similarity_avg",
        "answer_hash_stability_rate",
    }

    low_is_good = {
        "policy_violation_rate",
        "insufficient_evidence_rate",
        "tool_retry_rate",
        "attack_success_rate",
    }

    delta_metrics = {
        "schema_delta",
        "tool_success_delta",
        "policy_violation_delta",
        "insufficient_evidence_delta",
    }

    if key in high_is_good:
        if value >= 0.95:
            return "success", "Healthy"
        if value >= 0.75:
            return "warning", "Acceptable but worth watching"
        return "error", "Below desired threshold"

    if key in low_is_good:
        if value <= 0.05:
            return "success", "Healthy"
        if value <= 0.25:
            return "warning", "Elevated"
        return "error", "High"

    if key in delta_metrics:
        magnitude = abs(value)
        if magnitude <= 0.05:
            return "success", "Healthy"
        if magnitude <= 0.25:
            return "warning", "Elevated"
        return "error", "High"

    if key == "drift_score":
        if value <= 1:
            return "success", "Low drift"
        if value <= 10:
            return "warning", "Moderate drift"
        return "error", "High drift"

    return "info", "Informational metric"


def render_metric_card(col, label: str, value: Any, key_name: str) -> None:
    display = normalize_metric_display(value)
    col.metric(label, display)
    level, message = metric_status(key_name, value)
    with col:
        if level == "success":
            st.caption(f"✅ {message}")
        elif level == "warning":
            st.caption(f"⚠️ {message}")
        elif level == "error":
            st.caption(f"❌ {message}")
        else:
            st.caption(f"ℹ️ {message}")


def run_tabs_for_kind(run_kind: str) -> list[str]:
    if run_kind == "case_run":
        return ["Overview", "Events", "Output"]
    if run_kind == "drift":
        return ["Overview", "Drift"]
    if run_kind == "redteam":
        return ["Overview", "Red Team"]
    if run_kind == "reliability":
        return ["Overview"]
    return ["Overview", "Events", "Output", "Drift", "Red Team"]


def run_kind_description(run_kind: str) -> str:
    descriptions = {
        "case_run": "Single-case execution with output, evidence, and event trace.",
        "drift": "Model comparison run with metric deltas.",
        "redteam": "Adversarial evaluation run.",
        "reliability": "Fault injection / retry behavior run.",
        "generic": "Generic artifact directory.",
    }
    return descriptions.get(run_kind, "Generic artifact directory.")


def build_markdown_summary(
    run_dir: Path,
    run_kind: str,
    manifest: dict,
    metrics: dict,
    drift: dict | None,
    redteam: dict | None,
) -> str:
    lines = [
        "# LLM Reliability Lab Summary",
        "",
        f"- run_id: `{run_dir.name}`",
        f"- run_type: `{run_kind}`",
    ]

    if manifest:
        lines.extend(
            [
                f"- backend: `{manifest.get('backend', '—')}`",
                f"- model: `{manifest.get('model', '—')}`",
                f"- case_id: `{manifest.get('case_id', '—')}`",
            ]
        )

    if metrics:
        lines.extend(
            [
                "",
                "## Key Metrics",
            ]
        )
        for key in [
            "success_rate",
            "schema_compliance_rate",
            "tool_success_rate",
            "policy_violation_rate",
            "insufficient_evidence_rate",
            "citations_valid_rate",
            "answer_len",
        ]:
            if key in metrics:
                lines.append(f"- {key}: `{normalize_metric_display(metrics[key])}`")

    if drift:
        lines.extend(
            [
                "",
                "## Drift",
                f"- baseline: `{drift.get('baseline', '—')}`",
                f"- candidate: `{drift.get('candidate', '—')}`",
                f"- drift_score: `{normalize_metric_display(drift.get('drift_score'))}`",
            ]
        )

    if redteam:
        lines.extend(
            [
                "",
                "## Red Team",
                f"- attack_success_rate: `{normalize_metric_display(redteam.get('attack_success_rate'))}`",
                f"- n_attacks: `{redteam.get('n_attacks', '—')}`",
            ]
        )

    return "\n".join(lines)


def compare_metrics_df(
    metrics_a: dict,
    metrics_b: dict,
    label_a: str,
    label_b: str,
    show_all_metrics: bool = False,
) -> pd.DataFrame:
    preferred_keys = [
        "success_rate",
        "schema_compliance_rate",
        "tool_success_rate",
        "policy_violation_rate",
        "insufficient_evidence_rate",
        "citations_valid_rate",
        "answer_len",
        "llm_score_avg",
        "llm_helpfulness_avg",
        "llm_constraint_adherence_avg",
        "llm_evidence_use_avg",
        "answer_similarity_avg",
        "drift_score",
        "attack_success_rate",
        "recovery_rate",
        "tool_retry_rate",
    ]

    keys = sorted(set(metrics_a.keys()) | set(metrics_b.keys()))

    if not show_all_metrics:
        keys = [k for k in preferred_keys if k in keys]

    rows = []
    for key in keys:
        a = metrics_a.get(key)
        b = metrics_b.get(key)

        delta = None
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            delta = round(b - a, 3)

        rows.append(
            {
                "metric": str(key),
                label_a: normalize_metric_display(a),
                label_b: normalize_metric_display(b),
                "delta": delta if delta is not None else "—",
            }
        )

    df = pd.DataFrame(rows)

    for col in [label_a, label_b]:
        if col in df.columns:
            df[col] = df[col].astype(str)

    if "delta" in df.columns:
        df["delta"] = df["delta"].astype(str)

    return df


# --------------------------------------------------
# APP SETUP
# --------------------------------------------------


st.set_page_config(
    page_title="LLM Reliability Lab",
    layout="wide",
)

runs = list_runs()

if not runs:
    st.title("LLM Systems Reliability Lab")
    st.warning("No runs found under `runs/`.")
    st.stop()

counts = count_runs_by_type(runs)

latest_case = latest_run_by_type(runs, "case_run")
latest_drift = latest_run_by_type(runs, "drift")
latest_redteam = latest_run_by_type(runs, "redteam")

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.subheader("Inventory")
i1, i2 = st.sidebar.columns(2)
i1.metric("case_run", counts["case_run"])
i2.metric("drift", counts["drift"])
i3, i4 = st.sidebar.columns(2)
i3.metric("redteam", counts["redteam"])
i4.metric("reliability", counts["reliability"])

st.sidebar.divider()

st.sidebar.subheader("Filters")

run_type_filter = st.sidebar.selectbox(
    "Run type filter",
    ["all", "case_run", "drift", "redteam", "reliability"],
    index=0,
)

search_query = st.sidebar.text_input("Search run id", value="").strip().lower()

if run_type_filter == "all":
    filtered_runs = runs
else:
    filtered_runs = [r for r in runs if detect_run_kind(r) == run_type_filter]

if search_query:
    filtered_runs = [r for r in filtered_runs if search_query in r.name.lower()]

if not filtered_runs:
    st.title("LLM Systems Reliability Lab")
    st.warning("No runs match the current filter/search.")
    st.stop()

filtered_labels = [format_run_label(r) for r in filtered_runs]
filtered_label_to_dir = {format_run_label(r): r for r in filtered_runs}

st.sidebar.subheader("Quick select")
quick_choice = st.sidebar.selectbox(
    "Latest by type",
    [
        "none",
        "latest case_run",
        "latest drift",
        "latest redteam",
    ],
    index=0,
)

default_label = filtered_labels[0]

if quick_choice == "latest case_run" and latest_case:
    candidate = format_run_label(latest_case)
    if candidate in filtered_label_to_dir:
        default_label = candidate
elif quick_choice == "latest drift" and latest_drift:
    candidate = format_run_label(latest_drift)
    if candidate in filtered_label_to_dir:
        default_label = candidate
elif quick_choice == "latest redteam" and latest_redteam:
    candidate = format_run_label(latest_redteam)
    if candidate in filtered_label_to_dir:
        default_label = candidate

selected_label = st.sidebar.selectbox(
    "Run",
    filtered_labels,
    index=filtered_labels.index(default_label),
)

run_dir = filtered_label_to_dir[selected_label]
run_kind = detect_run_kind(run_dir)
file_groups = available_files_by_group(run_dir)

st.sidebar.divider()
st.sidebar.subheader("Run Info")
st.sidebar.caption(f"Selected type: `{run_kind}`")
st.sidebar.caption(run_kind_description(run_kind))

st.sidebar.subheader("Available files")
any_files = False
for group, files in file_groups.items():
    if files:
        any_files = True
        with st.sidebar.expander(group, expanded=False):
            for fname in files:
                st.markdown(f"- `{fname}`")
if not any_files:
    st.sidebar.caption("No known files found.")

# --------------------------------------------------
# LOAD CORE DATA
# --------------------------------------------------

metrics = load_json(run_dir / "metrics.json") or {}
step_metrics = load_json(run_dir / "step_metrics.json") or {}
manifest = load_json(run_dir / "run_manifest.json") or {}
reliability = load_json(run_dir / "reliability_report.json") or {}
events = load_events(run_dir / "events.jsonl")
output = load_json(run_dir / "output.json")
drift = load_json(run_dir / "drift_report_local.json") or load_json(run_dir / "drift_report.json")
redteam = load_json(run_dir / "redteam_report.json") or load_json(run_dir / "attack_report.json")

# --------------------------------------------------
# MAIN HEADER / LANDING
# --------------------------------------------------

st.title("LLM Systems Reliability Lab")

backend = manifest.get("backend", "—")
model = manifest.get("model", "—")

badge_color = {
    "case_run": "🟢",
    "drift": "🟣",
    "redteam": "🔴",
    "reliability": "🟠",
    "generic": "⚪",
}.get(run_kind, "⚪")

h1, h2, h3 = st.columns([2.2, 1.6, 1.2])

with h1:
    st.subheader(run_dir.name)
    st.caption(run_kind_description(run_kind))

with h2:
    st.markdown("**Backend / Model**")
    st.markdown(f"`{backend}` / `{model}`")

with h3:
    st.markdown("**Type**")
    st.markdown(f"{badge_color} `{run_kind}`")

st.caption(
    "Inspect evaluation, drift, red-team, and reliability artifacts generated under `runs/`."
)

l1, l2, l3, l4 = st.columns(4)
l1.metric("Total runs", len(runs))
l2.metric("Latest case run", latest_case.name if latest_case else "—")
l3.metric("Latest drift run", latest_drift.name if latest_drift else "—")
l4.metric("Latest redteam run", latest_redteam.name if latest_redteam else "—")

st.divider()

# --------------------------------------------------
# COMPARISON PANEL
# --------------------------------------------------

with st.expander("Compare two runs", expanded=False):
    compare_candidates = [format_run_label(r) for r in runs]
    compare_map = {format_run_label(r): r for r in runs}

    c1, c2 = st.columns(2)
    compare_a_label = c1.selectbox("Run A", compare_candidates, index=0, key="compare_a")
    compare_b_label = c2.selectbox(
        "Run B", compare_candidates, index=min(1, len(compare_candidates) - 1), key="compare_b"
    )

    compare_a_dir = compare_map[compare_a_label]
    compare_b_dir = compare_map[compare_b_label]

    metrics_a = load_json(compare_a_dir / "metrics.json") or {}
    metrics_b = load_json(compare_b_dir / "metrics.json") or {}

    show_all_metrics = st.checkbox("Show all metrics", value=False)

    if metrics_a or metrics_b:
        df_compare = compare_metrics_df(
            metrics_a,
            metrics_b,
            compare_a_dir.name,
            compare_b_dir.name,
            show_all_metrics=show_all_metrics,
        )
        st.dataframe(df_compare, width="stretch", hide_index=True)
    else:
        st.info("No comparable metrics.json found for the selected pair.")

# --------------------------------------------------
# EXPORT SUMMARY
# --------------------------------------------------

summary_md = build_markdown_summary(
    run_dir=run_dir,
    run_kind=run_kind,
    manifest=manifest,
    metrics=metrics,
    drift=drift,
    redteam=redteam,
)

with st.expander("Export markdown summary", expanded=False):
    st.code(summary_md, language="markdown")

st.divider()

visible_tab_names = run_tabs_for_kind(run_kind)

tab_objects = st.tabs(visible_tab_names)
tabs = dict(zip(visible_tab_names, tab_objects))

# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------

with tabs["Overview"]:
    st.subheader("Run Summary")
    st.caption("Core metadata extracted from `run_manifest.json` when available.")

    if run_kind == "drift" and drift:
        st.info("This overview is adapted for a model-comparison run.")
    elif run_kind == "redteam" and redteam:
        st.info("This overview is adapted for an adversarial evaluation run.")
    elif run_kind == "reliability" and reliability:
        st.info("This overview is adapted for a fault-injection / retry behavior run.")

    if run_kind == "case_run":
        if manifest:
            s1, s2, s3 = st.columns(3)
            s1.metric("Backend", manifest.get("backend", "—"))
            s2.metric("Model", manifest.get("model", "—"))
            s3.metric("Case ID", manifest.get("case_id", "—"))
        else:
            st.info("No run_manifest.json found for this run.")

    elif run_kind == "drift" and drift:
        s1, s2, s3 = st.columns(3)
        s1.metric("Drift score", normalize_metric_display(drift.get("drift_score")))
        s2.metric("Baseline", drift.get("baseline", "—"))
        s3.metric("Candidate", drift.get("candidate", "—"))

    elif run_kind == "redteam" and redteam:
        s1, s2 = st.columns(2)
        s1.metric(
            "Attack success rate", normalize_metric_display(redteam.get("attack_success_rate"))
        )
        s2.metric("Number of attacks", redteam.get("n_attacks", "—"))

    elif run_kind == "reliability" and reliability:
        s1, s2 = st.columns(2)
        s1.metric("Recovery rate", normalize_metric_display(reliability.get("recovery_rate")))
        s2.metric("Tool retry rate", normalize_metric_display(reliability.get("tool_retry_rate")))

    else:
        st.info("No summary metadata available for this run.")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Key Metrics")
        st.caption("Primary health indicators for the selected run.")

        m1, m2, m3, m4 = st.columns(4)

        if run_kind == "case_run":
            success_rate = metrics.get("success_rate")
            schema_rate = metrics.get("schema_compliance_rate")
            tool_rate = metrics.get("tool_success_rate")
            policy_rate = metrics.get("policy_violation_rate")

            render_metric_card(m1, "Success rate", success_rate, "success_rate")
            render_metric_card(m2, "Schema compliance", schema_rate, "schema_compliance_rate")
            render_metric_card(m3, "Tool success", tool_rate, "tool_success_rate")
            render_metric_card(m4, "Policy violations", policy_rate, "policy_violation_rate")

        elif run_kind == "drift" and drift:
            drift_score = drift.get("drift_score")
            similarity = drift.get("answer_similarity_avg")
            hash_stability = drift.get("answer_hash_stability_rate")
            schema_delta = drift.get("schema_delta")

            render_metric_card(m1, "Drift score", drift_score, "drift_score")
            render_metric_card(m2, "Answer similarity", similarity, "answer_similarity_avg")
            render_metric_card(m3, "Hash stability", hash_stability, "answer_hash_stability_rate")
            render_metric_card(m4, "Schema delta", schema_delta, "schema_delta")

        elif run_kind == "redteam" and redteam:
            attack_success_rate = redteam.get("attack_success_rate")
            n_attacks = redteam.get("n_attacks")
            blocked = None
            if isinstance(n_attacks, (int, float)) and isinstance(
                attack_success_rate, (int, float)
            ):
                blocked = round(n_attacks * (1 - attack_success_rate), 3)

            render_metric_card(
                m1, "Attack success rate", attack_success_rate, "attack_success_rate"
            )
            m2.metric("Number of attacks", normalize_metric_display(n_attacks))
            m3.metric("Blocked attacks", normalize_metric_display(blocked))
            m4.metric("Run type", "redteam")

            with m2:
                st.caption("ℹ️ Informational metric")
            with m3:
                st.caption("ℹ️ Informational metric")
            with m4:
                st.caption("ℹ️ Informational metric")

        elif run_kind == "reliability" and reliability:
            recovery_rate = reliability.get("recovery_rate")
            tool_retry_rate = reliability.get("tool_retry_rate")
            schema_rate = reliability.get("schema_compliance_rate")
            tool_rate = reliability.get("tool_success_rate")

            render_metric_card(m1, "Recovery rate", recovery_rate, "recovery_rate")
            render_metric_card(m2, "Tool retry rate", tool_retry_rate, "tool_retry_rate")
            render_metric_card(m3, "Schema compliance", schema_rate, "schema_compliance_rate")
            render_metric_card(m4, "Tool success", tool_rate, "tool_success_rate")

        else:
            m1.metric("Success rate", "—")
            m2.metric("Schema compliance", "—")
            m3.metric("Tool success", "—")
            m4.metric("Policy violations", "—")
            st.info("No primary metrics available for this run.")

        with st.expander("Raw metrics", expanded=False):
            if run_kind == "case_run":
                st.json(metrics or {})
            elif run_kind == "drift":
                st.json(drift or {})
            elif run_kind == "redteam":
                st.json(redteam or {})
            elif run_kind == "reliability":
                st.json(reliability or {})
            else:
                st.json({})

    with col2:
        if run_kind == "drift" and drift:
            st.subheader("Drift Signals")
            st.caption("Derived comparison fields from the drift report.")

            dcols = st.columns(2)
            dcols[0].metric(
                "Hash stability", normalize_metric_display(drift.get("answer_hash_stability_rate"))
            )
            dcols[1].metric(
                "Answer similarity", normalize_metric_display(drift.get("answer_similarity_avg"))
            )

            with st.expander("Open raw drift report summary", expanded=False):
                st.json(
                    {
                        "schema_delta": drift.get("schema_delta"),
                        "tool_success_delta": drift.get("tool_success_delta"),
                        "policy_violation_delta": drift.get("policy_violation_delta"),
                        "insufficient_evidence_delta": drift.get("insufficient_evidence_delta"),
                    }
                )

        elif run_kind == "redteam" and redteam:
            st.subheader("Red Team Snapshot")
            st.caption("Compact summary of adversarial results.")

            rows = redteam.get("attacks") or redteam.get("results") or []
            if rows:
                df_red_small = pd.DataFrame(rows)
                preferred_cols = [
                    c
                    for c in ["attack_id", "attack_success", "reason"]
                    if c in df_red_small.columns
                ]
                with st.expander("Open red team sample", expanded=True):
                    st.dataframe(df_red_small[preferred_cols], width="stretch", hide_index=True)
            else:
                st.info("No attack rows available for this run.")

        elif run_kind == "reliability" and reliability:
            st.subheader("Reliability Snapshot")
            st.caption("Fault-injection / retry summary.")

            with st.expander("Open reliability report", expanded=True):
                st.json(reliability)

        else:
            st.subheader("Step Metrics")
            st.caption("Per-step counts and average latency from `step_metrics.json`.")

            if step_metrics and "steps" in step_metrics and isinstance(step_metrics["steps"], dict):
                df_steps = pd.DataFrame(step_metrics["steps"]).T
                df_steps.index.name = "step"
                df_steps = df_steps.reset_index()

                numeric_cols = [
                    "count",
                    "success_count",
                    "failure_count",
                    "latency_ms_avg",
                ]
                for col in numeric_cols:
                    if col in df_steps.columns:
                        df_steps[col] = pd.to_numeric(df_steps[col], errors="coerce")

                if "latency_ms_avg" in df_steps.columns:
                    df_steps["latency_ms_avg"] = df_steps["latency_ms_avg"].round(3)

                display_cols = [
                    "step",
                    "count",
                    "success_count",
                    "failure_count",
                    "latency_ms_avg",
                ]
                existing = [c for c in display_cols if c in df_steps.columns]

                with st.expander("Open step metrics table", expanded=True):
                    st.dataframe(
                        df_steps[existing],
                        width="stretch",
                        hide_index=True,
                    )
            else:
                st.info("No step_metrics.json found for this run.")

# --------------------------------------------------
# EVENTS
# --------------------------------------------------

if "Events" in tabs:
    with tabs["Events"]:
        st.subheader("Event Timeline")
        st.caption("Execution trace from `events.jsonl`, with optional filtering.")

        if not events:
            st.info("No events found for this run.")
        else:
            df = pd.DataFrame(events)

            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Events", len(df))

            if "latency_ms" in df.columns:
                total_latency = df["latency_ms"].fillna(0).sum()
                e2.metric("Run latency (ms)", int(total_latency))
            else:
                e2.metric("Run latency (ms)", "—")

            if "step" in df.columns:
                e3.metric("Unique steps", df["step"].nunique())
            else:
                e3.metric("Unique steps", "—")

            if "error_type" in df.columns:
                error_count = df["error_type"].notna().sum()
                e4.metric("Events with errors", int(error_count))
            else:
                e4.metric("Events with errors", "—")

            if "timestamp_ms" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms")
                df = df.sort_values("timestamp_ms")
            else:
                df = df.reset_index(drop=True)

            st.divider()
            st.subheader("Filters")

            f1, f2, f3 = st.columns(3)

            if "step" in df.columns:
                step_options = ["all"] + sorted(df["step"].dropna().astype(str).unique().tolist())
            else:
                step_options = ["all"]

            if "event_type" in df.columns:
                event_options = ["all"] + sorted(
                    df["event_type"].dropna().astype(str).unique().tolist()
                )
            else:
                event_options = ["all"]

            success_options = ["all"]
            if "success" in df.columns:
                raw_success = [x for x in df["success"].dropna().unique().tolist()]
                if True in raw_success:
                    success_options.append("true")
                if False in raw_success:
                    success_options.append("false")

            selected_step = f1.selectbox("Step", step_options, index=0)
            selected_event_type = f2.selectbox("Event type", event_options, index=0)
            selected_success = f3.selectbox("Success", success_options, index=0)

            df_filtered = df.copy()

            if selected_step != "all" and "step" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["step"].astype(str) == selected_step]

            if selected_event_type != "all" and "event_type" in df_filtered.columns:
                df_filtered = df_filtered[
                    df_filtered["event_type"].astype(str) == selected_event_type
                ]

            if selected_success == "true" and "success" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["success"] == True]  # noqa: E712
            elif selected_success == "false" and "success" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["success"] == False]  # noqa: E712

            cols = [
                "timestamp",
                "step",
                "event_type",
                "latency_ms",
                "success",
                "error_type",
            ]
            existing_cols = [c for c in cols if c in df_filtered.columns]

            with st.expander("Open event table", expanded=True):
                st.dataframe(
                    df_filtered[existing_cols] if existing_cols else df_filtered,
                    width="stretch",
                    hide_index=True,
                )

            if (
                "latency_ms" in df.columns
                and "step" in df.columns
                and not df["latency_ms"].isna().all()
            ):
                st.divider()
                st.subheader("Latency by Step")
                chart = (
                    df.groupby("step")["latency_ms"].mean().sort_values(ascending=False).round(3)
                )
                st.bar_chart(chart, width="stretch")

# --------------------------------------------------
# OUTPUT
# --------------------------------------------------

if "Output" in tabs:
    with tabs["Output"]:
        st.subheader("Output Summary")
        st.caption("High-level view of the final response before the raw JSON.")

        if output:
            o1, o2, o3, o4, o5 = st.columns(5)
            o1.metric("Success", output.get("success", "—"))
            o2.metric("Insufficient evidence", output.get("insufficient_evidence", "—"))
            o3.metric("Citations", len(output.get("citation_ids", [])))
            o4.metric("Tool calls", len(output.get("tool_calls", [])))
            o5.metric("Policy violations", len(output.get("policy_violations", [])))

            st.markdown("**Answer**")
            st.write(output.get("answer", "—"))

            st.divider()

            col1, col2 = st.columns(2)

            with col1:
                with st.expander("Open output JSON", expanded=True):
                    st.json(output)

            with col2:
                if manifest:
                    with st.expander("Open manifest JSON", expanded=True):
                        st.json(manifest)
                else:
                    st.info("No run_manifest.json found for this run.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.info("No output.json found for this run.")
            with col2:
                if manifest:
                    with st.expander("Open manifest JSON", expanded=True):
                        st.json(manifest)
                else:
                    st.info("No run_manifest.json found for this run.")

# --------------------------------------------------
# DRIFT
# --------------------------------------------------

if "Drift" in tabs:
    with tabs["Drift"]:
        st.subheader("Drift Analysis")
        st.caption("Comparison between baseline and candidate model runs.")

        if not drift:
            st.info("No drift report found for this run.")
        else:
            d1, d2, d3 = st.columns(3)
            d1.metric("Drift score", normalize_metric_display(drift.get("drift_score")))
            d2.metric("Baseline", drift.get("baseline", "—"))
            d3.metric("Candidate", drift.get("candidate", "—"))

            if "deltas" in drift:
                df_drift = pd.DataFrame(drift["deltas"])

                st.divider()
                st.subheader("Metric Deltas")

                with st.expander("Open delta table", expanded=True):
                    st.dataframe(df_drift, width="stretch", hide_index=True)

                if "metric" in df_drift.columns and "delta" in df_drift.columns:
                    chart_df = df_drift.copy()
                    chart_df = chart_df[~chart_df["metric"].astype(str).str.startswith("_")]
                    chart_df["delta_abs"] = chart_df["delta"].abs()
                    chart_df = chart_df.sort_values("delta_abs", ascending=False)

                    st.divider()
                    st.subheader("Delta Magnitude by Metric")
                    chart_series = chart_df.set_index("metric")["delta_abs"]
                    st.bar_chart(chart_series, width="stretch")

            with st.expander("Open raw drift report", expanded=False):
                st.json(drift)

# --------------------------------------------------
# RED TEAM
# --------------------------------------------------

if "Red Team" in tabs:
    with tabs["Red Team"]:
        st.subheader("Red Team Analysis")
        st.caption("Adversarial attack outcomes for the selected run.")

        if not redteam:
            st.info("No red team report found for this run.")
        else:
            attack_success_rate = redteam.get("attack_success_rate")
            total_attacks = redteam.get("n_attacks", "—")

            r1, r2 = st.columns(2)
            r1.metric("Attack success rate", normalize_metric_display(attack_success_rate))
            r2.metric("Number of attacks", total_attacks)

            rows = None
            if "attacks" in redteam:
                rows = redteam["attacks"]
            elif "results" in redteam:
                rows = redteam["results"]

            if rows:
                st.divider()
                st.subheader("Attack Results")
                with st.expander("Open attack results table", expanded=True):
                    df_red = pd.DataFrame(rows)
                    st.dataframe(df_red, width="stretch", hide_index=True)

            with st.expander("Open raw red team report", expanded=False):
                st.json(redteam)
