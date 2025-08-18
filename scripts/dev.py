#!/usr/bin/env python3
"""
Development environment management script.
Unified interface for setting up, managing, and cleaning development environment.
"""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table

app = typer.Typer(
    name="dev",
    help="Development Environment Management Script",
    add_completion=False,
)
console = Console()

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
PRECOMMIT_CONFIG = PROJECT_ROOT / ".pre-commit-config.yaml"


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
def setup() -> None:
    """Set up development environment (install pre-commit hooks, etc.)."""
    panel = Panel.fit("🛠️ Setting Up Development Environment", style="blue")
    console.print(panel)

    setup_tasks = []

    # Install pre-commit hooks if config exists
    if PRECOMMIT_CONFIG.exists():
        with Status("Installing pre-commit hooks...", console=console, spinner="dots"):
            try:
                run_command(["pre-commit", "install"])
                setup_tasks.append("✅ Pre-commit hooks installed")
            except typer.Exit:
                setup_tasks.append("❌ Failed to install pre-commit hooks")
    else:
        setup_tasks.append("⚠️ No pre-commit config found")

    # Create any missing directories
    required_dirs = [
        PROJECT_ROOT / "tests" / "unit",
        PROJECT_ROOT / "tests" / "integration",
        PROJECT_ROOT / "docs" / "content",
    ]

    dirs_created = []
    for dir_path in required_dirs:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            dirs_created.append(str(dir_path.relative_to(PROJECT_ROOT)))

    if dirs_created:
        setup_tasks.append(f"✅ Created directories: {', '.join(dirs_created)}")

    # Show results
    console.print("[green]✅ Development environment setup completed![/green]")
    for task in setup_tasks:
        console.print(f"  • {task}")


@app.command()
def status() -> None:
    """Show development environment status."""
    panel = Panel.fit("📊 Development Environment Status", style="cyan")
    console.print(panel)

    table = Table(
        title="Development Environment", show_header=True, header_style="bold magenta"
    )
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    # Check Python version
    python_version = sys.version.split()[0]
    if python_version.startswith("3.12"):
        table.add_row("Python", "✅ Compatible", f"v{python_version}")
    else:
        table.add_row("Python", "⚠️ Version", f"v{python_version} (expected 3.12+)")

    # Check pixi
    try:
        result = run_command(["pixi", "--version"], capture_output=True)
        pixi_version = result.stdout.strip()
        table.add_row("Pixi", "✅ Available", pixi_version)
    except Exception:
        table.add_row("Pixi", "❌ Missing", "Install pixi package manager")

    # Check pre-commit
    if PRECOMMIT_CONFIG.exists():
        try:
            result = run_command(["pre-commit", "--version"], capture_output=True)
            precommit_version = result.stdout.strip().split()[-1]

            # Check if hooks are installed
            try:
                run_command(
                    ["pre-commit", "run", "--all-files", "--dry-run"],
                    capture_output=True,
                )
                table.add_row(
                    "Pre-commit", "✅ Ready", f"v{precommit_version}, hooks installed"
                )
            except Exception:
                table.add_row(
                    "Pre-commit",
                    "⚠️ Setup Needed",
                    f"v{precommit_version}, run 'pixi run dev setup'",
                )
        except Exception:
            table.add_row("Pre-commit", "❌ Missing", "Install pre-commit")
    else:
        table.add_row("Pre-commit", "⚠️ No Config", "No .pre-commit-config.yaml found")

    # Check git repository
    git_dir = PROJECT_ROOT / ".git"
    if git_dir.exists():
        try:
            result = run_command(["git", "status", "--porcelain"], capture_output=True)
            if result.stdout.strip():
                table.add_row("Git", "⚠️ Changes", "Uncommitted changes present")
            else:
                table.add_row("Git", "✅ Clean", "Working directory clean")
        except Exception:
            table.add_row("Git", "❌ Error", "Git command failed")
    else:
        table.add_row("Git", "❌ Not Initialized", "Run 'git init'")

    # Check key directories
    key_dirs = ["tests", "docs", "scripts", "logerr"]
    missing_dirs = [d for d in key_dirs if not (PROJECT_ROOT / d).exists()]

    if missing_dirs:
        table.add_row(
            "Project Structure", "⚠️ Incomplete", f"Missing: {', '.join(missing_dirs)}"
        )
    else:
        table.add_row("Project Structure", "✅ Complete", "All key directories present")

    console.print(table)


@app.command()
def hooks(
    action: str = typer.Argument(
        ..., help="Action to perform: install, uninstall, run, update"
    ),
) -> None:
    """Manage pre-commit hooks."""
    if not PRECOMMIT_CONFIG.exists():
        console.print("[red]❌ No .pre-commit-config.yaml found[/red]")
        raise typer.Exit(1)

    actions = {
        "install": (["pre-commit", "install"], "Installing pre-commit hooks..."),
        "uninstall": (["pre-commit", "uninstall"], "Uninstalling pre-commit hooks..."),
        "run": (["pre-commit", "run", "--all-files"], "Running pre-commit hooks..."),
        "update": (["pre-commit", "autoupdate"], "Updating pre-commit hooks..."),
    }

    if action not in actions:
        console.print(f"[red]❌ Invalid action: {action}[/red]")
        console.print(f"Available actions: {', '.join(actions.keys())}")
        raise typer.Exit(1)

    cmd, message = actions[action]
    console.print(f"🔧 {message}")

    with Status(message, console=console, spinner="dots"):
        run_command(cmd)

    console.print(f"[green]✅ Pre-commit {action} completed![/green]")


@app.command()
def clean() -> None:
    """Clean development artifacts."""
    console.print("🧹 Cleaning development artifacts...")

    artifacts_cleaned = []

    # Clean Python cache files
    pycache_dirs = list(PROJECT_ROOT.rglob("__pycache__"))
    for pycache_dir in pycache_dirs:
        if pycache_dir.is_dir():
            import shutil

            shutil.rmtree(pycache_dir)
            artifacts_cleaned.append(
                f"Python cache: {pycache_dir.relative_to(PROJECT_ROOT)}"
            )

    # Clean .pyc files
    pyc_files = list(PROJECT_ROOT.rglob("*.pyc"))
    for pyc_file in pyc_files:
        pyc_file.unlink()
        artifacts_cleaned.append(
            f"Compiled Python: {pyc_file.relative_to(PROJECT_ROOT)}"
        )

    # Clean .pyo files
    pyo_files = list(PROJECT_ROOT.rglob("*.pyo"))
    for pyo_file in pyo_files:
        pyo_file.unlink()
        artifacts_cleaned.append(
            f"Optimized Python: {pyo_file.relative_to(PROJECT_ROOT)}"
        )

    # Clean mypy cache
    mypy_cache = PROJECT_ROOT / ".mypy_cache"
    if mypy_cache.exists():
        import shutil

        shutil.rmtree(mypy_cache)
        artifacts_cleaned.append("MyPy cache")

    # Clean ruff cache
    ruff_cache = PROJECT_ROOT / ".ruff_cache"
    if ruff_cache.exists():
        import shutil

        shutil.rmtree(ruff_cache)
        artifacts_cleaned.append("Ruff cache")

    # Clean any .DS_Store files (macOS)
    ds_store_files = list(PROJECT_ROOT.rglob(".DS_Store"))
    for ds_file in ds_store_files:
        ds_file.unlink()
        artifacts_cleaned.append(f"macOS metadata: {ds_file.relative_to(PROJECT_ROOT)}")

    if artifacts_cleaned:
        console.print("[green]✅ Cleaned development artifacts:[/green]")
        for artifact in artifacts_cleaned:
            console.print(f"  • {artifact}")
    else:
        console.print("[yellow]⚠️ No development artifacts to clean[/yellow]")


if __name__ == "__main__":
    # Change to project root directory
    import os

    os.chdir(PROJECT_ROOT)
    app()
