import typer

app = typer.Typer(help="LLM Systems Reliability Lab CLI")

@app.callback()
def main() -> None:
    """
    LLM Systems Reliability Lab CLI.
    """
    pass

@app.command()
def demo(
    backend: str = typer.Option("mock", help="Backend name"),
    model: str = typer.Option("mock", help="Model name"),
) -> None:
    """
    Demo stub. In later steps this will execute an end-to-end run and write artifacts to runs/<id>/.
    """
    typer.echo(f"demo called: backend={backend} model={model}")

if __name__ == "__main__":
    app()