#!/usr/bin/env python3
"""
Testing management script with pytest.
Unified interface for all testing tasks including unit, integration, and documentation.
"""

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

app = typer.Typer(
    name="test",
    help="Testing Management Script",
    add_completion=False,
)

console = Console()

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
DOCS_DIR = PROJECT_ROOT / "docs"


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
def unit(
    coverage: bool = typer.Option(
        True, "--coverage/--no-coverage", help="Generate coverage report"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    fail_fast: bool = typer.Option(
        False, "--fail-fast", "-x", help="Stop on first failure"
    ),
) -> None:
    """Run unit tests."""
    panel = Panel.fit("🧪 Running Unit Tests", style="blue")
    console.print(panel)

    cmd = ["pytest", "tests/", "-m", "unit"]

    if verbose:
        cmd.append("-v")
    if fail_fast:
        cmd.append("-x")
    if coverage:
        cmd.extend(
            [
                "--cov=logerr",
                "--cov-report=term",
                "--cov-report=xml",
                "--cov-report=html",
            ]
        )

    with Status("Running unit tests...", console=console, spinner="dots"):
        run_command(cmd)

    console.print("[green]✅ Unit tests completed![/green]")


@app.command()
def integration(
    coverage: bool = typer.Option(
        True, "--coverage/--no-coverage", help="Generate coverage report"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Run integration tests."""
    panel = Panel.fit("🔗 Running Integration Tests", style="blue")
    console.print(panel)

    cmd = ["pytest", "tests/", "-m", "integration"]

    if verbose:
        cmd.append("-v")
    if coverage:
        cmd.extend(
            [
                "--cov=logerr",
                "--cov-report=term",
                "--cov-report=xml",
                "--cov-report=html",
            ]
        )

    with Status("Running integration tests...", console=console, spinner="dots"):
        run_command(cmd)

    console.print("[green]✅ Integration tests completed![/green]")


@app.command()
def all(
    coverage: bool = typer.Option(
        True, "--coverage/--no-coverage", help="Generate coverage report"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Run all tests (unit + integration + docs)."""
    panel = Panel.fit("🚀 Running All Tests", style="blue")
    console.print(panel)

    cmd = [
        "pytest",
        "tests/",
        "docs/",
        "README.md",
        "--doctest-modules",
        "logerr",
        "--doctest-glob=*.md",
        "-m",
        "not slow",
    ]

    if verbose:
        cmd.append("-v")
    if coverage:
        cmd.extend(
            [
                "--cov=logerr",
                "--cov-report=term",
                "--cov-report=xml",
                "--cov-report=html",
            ]
        )

    with Status("Running all tests...", console=console, spinner="dots"):
        run_command(cmd)

    console.print("[green]✅ All tests completed![/green]")


@app.command()
def fast(
    coverage: bool = typer.Option(
        True, "--coverage/--no-coverage", help="Generate coverage report"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Run fast tests (excludes slow tests)."""
    panel = Panel.fit("⚡ Running Fast Tests", style="blue")
    console.print(panel)

    cmd = ["pytest", "tests/", "--doctest-modules", "logerr", "-m", "not slow"]

    if verbose:
        cmd.append("-v")
    if coverage:
        cmd.extend(
            [
                "--cov=logerr",
                "--cov-report=term",
                "--cov-report=xml",
                "--cov-report=html",
            ]
        )

    with Status("Running fast tests...", console=console, spinner="dots"):
        run_command(cmd)

    console.print("[green]✅ Fast tests completed![/green]")


@app.command()
def clean() -> None:
    """Clean test artifacts (coverage reports, pytest cache, etc.)."""
    console.print("🧹 Cleaning test artifacts...")

    artifacts_cleaned = []

    # Clean coverage reports
    coverage_dirs = [PROJECT_ROOT / "htmlcov", PROJECT_ROOT / ".coverage"]
    for path in coverage_dirs:
        if path.exists():
            if path.is_dir():
                import shutil

                shutil.rmtree(path)
                artifacts_cleaned.append(f"Coverage directory: {path.name}")
            else:
                path.unlink()
                artifacts_cleaned.append(f"Coverage file: {path.name}")

    # Clean pytest cache
    pytest_cache = PROJECT_ROOT / ".pytest_cache"
    if pytest_cache.exists():
        import shutil

        shutil.rmtree(pytest_cache)
        artifacts_cleaned.append("Pytest cache")

    # Clean any .pyc files and __pycache__ directories
    for pyc_file in PROJECT_ROOT.rglob("*.pyc"):
        pyc_file.unlink()
        artifacts_cleaned.append(f"Compiled Python file: {pyc_file.name}")

    pycache_dirs = list(PROJECT_ROOT.rglob("__pycache__"))
    for pycache_dir in pycache_dirs:
        if pycache_dir.is_dir():
            import shutil

            shutil.rmtree(pycache_dir)
            artifacts_cleaned.append(f"Python cache: {pycache_dir}")

    if artifacts_cleaned:
        console.print("[green]✅ Cleaned test artifacts:[/green]")
        for artifact in artifacts_cleaned:
            console.print(f"  • {artifact}")
    else:
        console.print("[yellow]⚠️ No test artifacts to clean[/yellow]")


if __name__ == "__main__":
    # Change to project root directory
    import os

    os.chdir(PROJECT_ROOT)
    app()
