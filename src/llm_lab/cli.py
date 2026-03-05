from __future__ import annotations

from pathlib import Path

import json
import typer

from llm_lab.schemas.export import export_output_schema

app = typer.Typer(help="LLM Systems Reliability Lab CLI")


@app.callback()
def main() -> None:
    """
    LLM Systems Reliability Lab CLI.
    """
    pass


@app.command()
def schemas(out_dir: str = typer.Option("src/llm_lab/schemas")) -> None:
    """
    Export JSON Schemas used by the lab (contract-first).
    """
    out_path = Path(out_dir) / "Output.schema.json"
    export_output_schema(out_path)
    typer.echo(f"Wrote: {out_path}")


@app.command()
def demo(
    backend: str = typer.Option("mock"),
    model: str = typer.Option("mock"),
    case_id: str = typer.Option("c1"),
) -> None:
    """
    Run an end-to-end demo and write artifacts to runs/<run_id>/.
    """
    from llm_lab.pipeline.contracts import Case
    from llm_lab.pipeline.sut import PipelineConfig, SUTPipeline

    # Minimal case loader (MVP): pick from data/benchmarks/cases.jsonl by id
    cases_path = Path("data") / "benchmarks" / "cases.jsonl"
    rows = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    row = next((r for r in rows if r["case_id"] == case_id), None)
    if row is None:
        raise typer.BadParameter(f"Unknown case_id={case_id}")

    case = Case(case_id=row["case_id"], prompt=row["prompt"], expected=row.get("expected", {}))

    cfg = PipelineConfig(backend=backend, model=model)
    pipe = SUTPipeline(cfg=cfg)
    out, out_dir = pipe.run(case)

    typer.echo(f"run_dir={out_dir}")
    typer.echo(f"success={out.success} insufficient_evidence={out.insufficient_evidence}")

@app.command()
def eval(
    suite: str = typer.Option("reliability"),
    fault_matrix: str = typer.Option("configs/fault_matrix.yaml"),
) -> None:
    """
    Run evaluation suites.
    """
    if suite != "reliability":
        raise typer.BadParameter("Only suite=reliability implemented in MVP")

    from llm_lab.evals.reliability import run_reliability_suite

    out_dir = run_reliability_suite(Path(fault_matrix))
    typer.echo(f"run_dir={out_dir}")
    typer.echo("wrote=reliability_report.json metrics.json")

@app.command()
def redteam(
    config: str = typer.Option("configs/redteam_suite.yaml"),
    backend: str = typer.Option("mock"),
    model: str = typer.Option("mock"),
) -> None:
    """
    Run the red team suite and write attack_report.json under runs/<id>/.
    """
    from llm_lab.redteam.runner import run_redteam_suite

    out_dir = run_redteam_suite(Path(config), backend=backend, model=model)
    typer.echo(f"run_dir={out_dir}")
    typer.echo("wrote=attack_report.json")
    
@app.command()
def drift(
    matrix: str = typer.Option("configs/drift_matrix.yaml"),
) -> None:
    """
    Run drift observatory and write drift_report.json + drift_report.md.
    """
    from llm_lab.drift.runner import run_drift

    out_dir = run_drift(Path(matrix))
    typer.echo(f"run_dir={out_dir}")
    typer.echo("wrote=drift_report.json drift_report.md")

if __name__ == "__main__":
    app()