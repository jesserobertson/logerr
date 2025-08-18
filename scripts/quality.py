#!/usr/bin/env python3
"""Code quality management script for logerr project."""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

app = typer.Typer(help="Code quality management for logerr")
console = Console()

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_DIRS = ["logerr", "tests", "scripts"]


def run_command(cmd: list[str]) -> int:
    """Run a command with enhanced output."""
    console.print(f"Running: [bold cyan]{' '.join(cmd)}[/bold cyan]")
    result = subprocess.run(cmd)
    return result.returncode


@app.command()
def lint(
    fix: bool = typer.Option(False, help="Automatically fix issues"),
) -> None:
    """Run linting checks."""
    cmd = ["ruff", "check"] + SOURCE_DIRS

    if fix:
        cmd.append("--fix")

    console.print(Panel("Running linting checks", style="bold blue"))
    sys.exit(run_command(cmd))


@app.command()
def format(
    check: bool = typer.Option(False, help="Check formatting without making changes"),
) -> None:
    """Format code or check formatting."""
    cmd = ["ruff", "format"]

    if check:
        cmd.append("--check")

    cmd.extend(SOURCE_DIRS)

    action = "Checking" if check else "Formatting"
    console.print(Panel(f"{action} code", style="bold blue"))
    sys.exit(run_command(cmd))


@app.command("format-check")
def format_check() -> None:
    """Check code formatting without making changes."""
    format(check=True)


@app.command()
def typecheck(
    strict: bool = typer.Option(False, help="Enable strict mode"),
) -> None:
    """Run type checking."""
    cmd = ["mypy", "logerr"]

    if strict:
        cmd.append("--strict")

    console.print(Panel("Running type checks", style="bold blue"))
    sys.exit(run_command(cmd))


@app.command()
def check() -> None:
    """Run all quality checks (typecheck + lint + format check)."""
    panel = Panel.fit("🔍 Running All Code Quality Checks", style="blue")
    console.print(panel)

    results = {}

    # Type checking
    with Status("Running mypy type checking...", console=console, spinner="dots"):
        try:
            run_command(["mypy", "logerr"])
            results["typecheck"] = "✅ Pass"
        except typer.Exit:
            results["typecheck"] = "❌ Fail"

    # Linting
    with Status("Running ruff linting...", console=console, spinner="dots"):
        try:
            run_command(["ruff", "check"] + SOURCE_DIRS)
            results["lint"] = "✅ Pass"
        except typer.Exit:
            results["lint"] = "❌ Fail"

    # Format checking
    with Status("Checking code formatting...", console=console, spinner="dots"):
        try:
            run_command(["ruff", "format", "--check"] + SOURCE_DIRS)
            results["format"] = "✅ Pass"
        except typer.Exit:
            results["format"] = "❌ Fail"

    # Results table
    from rich.table import Table

    table = Table(
        title="Quality Check Results", show_header=True, header_style="bold magenta"
    )
    table.add_column("Check", style="cyan")
    table.add_column("Result", justify="center")

    table.add_row("Type Check", results["typecheck"])
    table.add_row("Linting", results["lint"])
    table.add_row("Formatting", results["format"])

    console.print(table)

    # Exit with error if any check failed
    if "❌ Fail" in results.values():
        console.print("\n[red]❌ Some quality checks failed[/red]")
        raise typer.Exit(1)
    else:
        console.print("\n[green]✅ All quality checks passed![/green]")


@app.command()
def fix() -> None:
    """Auto-fix all possible issues (format + lint --fix)."""
    console.print("🔧 Auto-fixing code issues...")

    # Format code
    with Status("Formatting code...", console=console, spinner="dots"):
        run_command(["ruff", "format"] + SOURCE_DIRS)

    # Fix linting issues
    with Status("Fixing linting issues...", console=console, spinner="dots"):
        run_command(["ruff", "check", "--fix"] + SOURCE_DIRS)

    console.print("[green]✅ Auto-fix completed![/green]")
    console.print(
        "[yellow]💡 Run 'pixi run quality check' to verify all issues are resolved[/yellow]"
    )


@app.command()
def all(
    fix: bool = typer.Option(False, help="Automatically fix linting issues"),
) -> None:
    """Run all quality checks."""
    check()


@app.command()
def pre_commit() -> None:
    """Run pre-commit hooks on all files."""
    console.print(Panel("Running pre-commit hooks", style="bold blue"))
    sys.exit(run_command(["pre-commit", "run", "--all-files"]))


@app.command()
def install_hooks() -> None:
    """Install pre-commit hooks."""
    console.print(Panel("Installing pre-commit hooks", style="bold blue"))
    sys.exit(run_command(["pre-commit", "install"]))


def main() -> None:
    """Main entry point - defaults to all quality checks."""
    if len(sys.argv) == 1:
        # No arguments provided, run all checks
        all()
    else:
        app()


if __name__ == "__main__":
    main()
