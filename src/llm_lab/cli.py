from __future__ import annotations

from pathlib import Path

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
def demo(backend: str = typer.Option("mock"), model: str = typer.Option("mock")) -> None:
    """
    Demo stub. In later steps this will execute an end-to-end run and write artifacts to runs/<id>/.
    """
    typer.echo(f"demo called: backend={backend} model={model}")


if __name__ == "__main__":
    app()