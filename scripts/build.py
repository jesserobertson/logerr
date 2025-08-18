#!/usr/bin/env python3
"""
Build and distribution management script.
Unified interface for packaging, building, and uploading.
"""

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table

app = typer.Typer(
    name="build",
    help="Build and Distribution Management Script",
    add_completion=False,
)
console = Console()

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


def run_command(
    cmd: list[str], capture_output: bool = False, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a shell command with proper error handling."""
    try:
        if capture_output:
            return subprocess.run(
                cmd, capture_output=True, text=True, check=check, cwd=PROJECT_ROOT
            )
        else:
            return subprocess.run(cmd, check=check, cwd=PROJECT_ROOT)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Command failed: {' '.join(cmd)}[/red]")
        if capture_output and e.stdout:
            console.print(f"[yellow]STDOUT: {e.stdout}[/yellow]")
        if capture_output and e.stderr:
            console.print(f"[red]STDERR: {e.stderr}[/red]")
        raise typer.Exit(1) from e


@app.command()
def package() -> None:
    """Build wheel and source distribution."""
    panel = Panel.fit("📦 Building Package", style="blue")
    console.print(panel)

    # Clean previous builds
    console.print("🧹 Cleaning previous builds...")
    clean()

    # Build package
    with Status("Building package...", console=console, spinner="dots"):
        run_command(["python", "-m", "build"])

    # Show what was built
    if DIST_DIR.exists():
        files = list(DIST_DIR.glob("*"))
        if files:
            console.print("[green]✅ Package built successfully![/green]")
            console.print("\n[bold]Built files:[/bold]")
            for file in files:
                console.print(f"  • {file.name}")
        else:
            console.print("[red]❌ No files were built[/red]")
            raise typer.Exit(1)
    else:
        console.print("[red]❌ Build directory not created[/red]")
        raise typer.Exit(1)


@app.command()
def upload(
    repository: str = typer.Option(
        "pypi", "--repository", "-r", help="Repository to upload to (pypi, testpypi)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Perform a dry run without actually uploading"
    ),
) -> None:
    """Upload package to PyPI."""
    if not DIST_DIR.exists() or not list(DIST_DIR.glob("*")):
        console.print(
            "[red]❌ No built packages found. Run 'pixi run build package' first.[/red]"
        )
        raise typer.Exit(1)

    panel = Panel.fit(f"🚀 Uploading to {repository.upper()}", style="blue")
    console.print(panel)

    cmd = ["twine", "upload", "--repository", repository]
    if dry_run:
        cmd.append("--dry-run")
    cmd.append(str(DIST_DIR / "*"))

    with Status(f"Uploading to {repository}...", console=console, spinner="dots"):
        run_command(cmd)

    if dry_run:
        console.print("[green]✅ Dry run completed successfully![/green]")
    else:
        console.print(f"[green]✅ Package uploaded to {repository}![/green]")


@app.command()
def check() -> None:
    """Check package for common issues."""
    if not DIST_DIR.exists() or not list(DIST_DIR.glob("*")):
        console.print(
            "[red]❌ No built packages found. Run 'pixi run build package' first.[/red]"
        )
        raise typer.Exit(1)

    panel = Panel.fit("🔍 Checking Package", style="blue")
    console.print(panel)

    with Status("Checking package...", console=console, spinner="dots"):
        run_command(["twine", "check", str(DIST_DIR / "*")])

    console.print("[green]✅ Package check completed![/green]")


@app.command()
def status() -> None:
    """Show build status and information."""
    panel = Panel.fit("📊 Build Status", style="cyan")
    console.print(panel)

    # Check if build directories exist
    table = Table(
        title="Build Information", show_header=True, header_style="bold magenta"
    )
    table.add_column("Item", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    # Check dist directory
    if DIST_DIR.exists():
        files = list(DIST_DIR.glob("*"))
        if files:
            table.add_row("Distribution", "✅ Ready", f"{len(files)} files")
            for file in files:
                table.add_row("", "", f"  • {file.name}")
        else:
            table.add_row("Distribution", "⚠️ Empty", "No files")
    else:
        table.add_row("Distribution", "❌ Missing", "Not built")

    # Check build directory
    if BUILD_DIR.exists():
        table.add_row("Build Cache", "✅ Present", "Build artifacts exist")
    else:
        table.add_row("Build Cache", "✅ Clean", "No build artifacts")

    console.print(table)


@app.command()
def clean() -> None:
    """Clean build artifacts."""
    console.print("🧹 Cleaning build artifacts...")

    artifacts_cleaned = []

    # Clean dist directory
    if DIST_DIR.exists():
        import shutil

        shutil.rmtree(DIST_DIR)
        artifacts_cleaned.append("Distribution directory")

    # Clean build directory
    if BUILD_DIR.exists():
        import shutil

        shutil.rmtree(BUILD_DIR)
        artifacts_cleaned.append("Build directory")

    # Clean egg-info directories
    egg_info_dirs = list(PROJECT_ROOT.glob("*.egg-info"))
    for egg_dir in egg_info_dirs:
        if egg_dir.is_dir():
            import shutil

            shutil.rmtree(egg_dir)
            artifacts_cleaned.append(f"Egg info: {egg_dir.name}")

    if artifacts_cleaned:
        console.print("[green]✅ Cleaned build artifacts:[/green]")
        for artifact in artifacts_cleaned:
            console.print(f"  • {artifact}")
    else:
        console.print("[yellow]⚠️ No build artifacts to clean[/yellow]")


if __name__ == "__main__":
    # Change to project root directory
    import os

    os.chdir(PROJECT_ROOT)
    app()
