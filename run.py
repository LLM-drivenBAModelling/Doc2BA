#!/usr/bin/env python3
"""
Launch script for doc2ba - choose between CLI or Web UI
"""

import os
import sys
import subprocess
import typer

app = typer.Typer(help="doc2ba launcher - choose between CLI or Web UI")

@app.command()
def ui():
    """Launch the Streamlit web UI"""
    print("Starting doc2ba Web UI...")
    subprocess.run(["streamlit", "run", "streamlit_app.py"])

@app.command()
def cli(
    input: str = typer.Option(..., help="Path to file or directory containing PDFs/TXT/MD"),
    provider: str = typer.Option("openai", help="LLM provider: openai|anthropic|azure"),
    model: str = typer.Option("gpt-4o-mini", help="Model or deployment name"),
    output: str = typer.Option(None, help="Optional JSON output path"),
):
    """Run the CLI pipeline"""
    cmd = ["python", "cli.py", "run", "--input", input, "--provider", provider, "--model", model]
    if output:
        cmd.extend(["--output", output])
    subprocess.run(cmd)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Launch menu if no command is provided"""
    if ctx.invoked_subcommand is None:
        print("\ndoc2ba: Multi-Agent Business Architecture Miner")
        print("=" * 50)
        print("\nHow would you like to use doc2ba?\n")
        print("1. Web UI (Streamlit interface)")
        print("2. CLI (Command-line interface)")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            ui()
        elif choice == "2":
            print("\nTo use the CLI, run one of these commands:")
            print("\npython run.py cli --input ./test_files --provider openai --model gpt-4o-mini")
            print("python run.py cli --help  # For more options")
        elif choice == "3":
            print("\nExiting.")
            sys.exit(0)
        else:
            print("\nInvalid choice. Please run again.")

if __name__ == "__main__":
    app()
