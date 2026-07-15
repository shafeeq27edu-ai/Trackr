import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from trackr_sdk.client import TrackrClient

app = typer.Typer(help="Trackr CLI - Manage your computer vision tracking platform")
console = Console()

# We can store client instance here globally for commands to use if needed
client: Optional[TrackrClient] = None


@app.callback()
def main(
    url: str = typer.Option("http://localhost:8000", help="Trackr API URL"),
    token: str = typer.Option(None, envvar="TRACKR_TOKEN", help="Trackr API Token"),
):
    """
    Trackr CLI
    """
    global client
    client = TrackrClient(base_url=url, token=token)


@app.command()
def init():
    """Scaffold a new Trackr project or plugin."""
    console.print("[green]Initialized a new Trackr environment.[/green]")
    console.print("To create a plugin, see the documentation at https://docs.trackr.io/plugins")


@app.command()
def models():
    """List available models."""
    try:
        data = client.list_models()
        table = Table("Model ID")
        for model in data.get("models", []):
            table.add_row(model)
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error fetching models: {e}[/red]")


@app.command()
def plugins():
    """List available plugins."""
    try:
        data = client.list_plugins()
        table = Table("Plugin Name", "Version", "Category")
        for p in data.get("plugins", []):
            table.add_row(p.get("name"), p.get("version"), p.get("category"))
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error fetching plugins: {e}[/red]")


@app.command()
def analyze(video_path: str, project_id: Optional[str] = typer.Option(None, help="Project ID")):
    """Submit a video for full analytics processing."""
    try:
        job = client.submit_job(filename=video_path, project_id=project_id)
        console.print(f"[green]Job submitted successfully![/green]")
        console.print(f"Job ID: {job.id}")
        console.print(f"Status: {job.status.value}")
    except Exception as e:
        console.print(f"[red]Error submitting job: {e}[/red]")


@app.command()
def status(job_id: str):
    """Check the status of a specific job."""
    try:
        job = client.get_job(job_id)
        console.print(f"Job ID: [bold]{job.id}[/bold]")
        console.print(f"Status: [cyan]{job.status.value}[/cyan]")
        console.print(f"Progress: {job.progress}%")
        console.print(f"Stage: {job.stage}")
        if job.error:
            console.print(f"Error: [red]{job.error}[/red]")
    except Exception as e:
        console.print(f"[red]Error getting job status: {e}[/red]")


if __name__ == "__main__":
    app()
