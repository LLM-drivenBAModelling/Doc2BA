from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from ba_agents.classification_agent import ClassificationAgent
from ba_agents.categorization_agent import CategorizationAgent
from ba_agents.extraction_agent import ExtractionAgent
from ba_agents.inference_agent import InferenceAgent
from models.schemas import (
    BusinessArtefact,
    CategorizedSentence,
    CategorizationResult,
    ClassificationResult,
    ExtractionResult,
    InferenceResult,
)
from utils.csv_artefacts import CsvArtefactError, classification_from_csv
from utils.loaders import DocumentChunk, load_inputs


app = typer.Typer(help="doc2ba: Multi-Agent Business Architecture Miner")
console = Console()


def _assign_sentence_ids(extraction_pairs) -> ExtractionResult:
    sentences = []
    for chunk, candidates in extraction_pairs:
        # Ensure candidates is not None and has a sentences attribute
        if candidates and hasattr(candidates, 'sentences'):
            for cand in candidates.sentences:
                sid = str(uuid.uuid4())[:8]
                sentences.append({
                    "id": sid,
                    "text": cand.text,
                    "source": chunk.source,
                    "page": chunk.page,
                    "confidence": cand.confidence,
                })
    
    # Always return a valid ExtractionResult, even if empty
    return ExtractionResult(sentences=[
        # type: ignore[arg-type]
        # Pydantic v1 will coerce dicts to models
        s for s in sentences
    ])


def _print_extraction(res: ExtractionResult):
    table = Table(title="Extracted Sentences")
    table.add_column("id")
    table.add_column("source:page")
    table.add_column("confidence")
    table.add_column("text")
    
    if not res.sentences:
        console.print("[yellow]No sentences extracted[/yellow]")
        return
        
    for s in res.sentences[:50]:
        table.add_row(s.id, f"{s.source}:{s.page}", f"{s.confidence:.2f}", s.text[:120])
    console.print(table)


def _print_categorization(res: CategorizationResult):
    table = Table(title="Categorized Sentences")
    table.add_column("id")
    table.add_column("source:page")
    table.add_column("category")
    table.add_column("cat. conf")
    table.add_column("text")
    
    if not res.sentences:
        console.print("[yellow]No sentences categorized[/yellow]")
        return
        
    for s in res.sentences[:50]:
        table.add_row(
            s.id, 
            f"{s.source}:{s.page}", 
            s.category.value, 
            f"{s.category_confidence:.2f}", 
            s.text[:100]
        )
    console.print(table)


def _print_classification(res: ClassificationResult):
    table = Table(title="Classified Artefacts")
    table.add_column("id")
    table.add_column("type")
    table.add_column("conf")
    table.add_column("name")
    for a in res.artefacts[:50]:
        table.add_row(a.id, a.type.value, f"{a.confidence:.2f}", a.name[:80])
    console.print(table)


def _print_inference(res: InferenceResult):
    table_a = Table(title="Inferred Artefacts")
    table_a.add_column("id")
    table_a.add_column("type")
    table_a.add_column("conf")
    table_a.add_column("name")
    for a in res.new_artefacts[:50]:
        table_a.add_row(a.id, a.type.value, f"{a.confidence:.2f}", a.name[:80])
    console.print(table_a)

    table_r = Table(title="Inferred Relationships")
    table_r.add_column("source")
    table_r.add_column("type")
    table_r.add_column("target")
    table_r.add_column("conf")
    for r in res.relationships[:100]:
        table_r.add_row(r.source_id, r.type, r.target_id, f"{r.confidence:.2f}")
    console.print(table_r)


@app.command()
def run(
    input: str = typer.Option(..., help="Path to file or directory containing PDFs/TXT/MD"),
    provider: Optional[str] = typer.Option(None, help="LLM provider: openai|anthropic|azure"),
    model: Optional[str] = typer.Option(None, help="Model or deployment name"),
    output: Optional[str] = typer.Option(None, help="Optional JSON output path"),
):
    """Run the 3-stage pipeline: extract -> classify -> infer."""
    load_dotenv()

    console.rule("[bold]Loading inputs")
    chunks: List[DocumentChunk] = load_inputs(input)
    if not chunks:
        console.print("No supported files found.")
        raise typer.Exit(code=1)

    console.rule("[bold]Extraction")
    extractor = ExtractionAgent(provider=provider, model=model)
    extraction_pairs = extractor.run(chunks)
    extraction_result = _assign_sentence_ids(extraction_pairs)
    _print_extraction(extraction_result)

    console.rule("[bold]Categorization")
    # Skip categorization if no sentences were extracted
    if not extraction_result.sentences:
        console.print("[yellow]No sentences to categorize, skipping categorization step[/yellow]")
        categorization_result = CategorizationResult(sentences=[])
    else:
        # Create a dictionary with sentence details for categorization
        sentence_details = {
            s.id: {
                "text": s.text,
                "source": s.source,
                "page": s.page,
                "confidence": s.confidence
            } for s in extraction_result.sentences
        }
        
        categorizer = CategorizationAgent(provider=provider, model=model)
        categorization_result = categorizer.run(sentence_details)
    
    _print_categorization(categorization_result)
    
    console.rule("[bold]Classification")
    # Skip classification if no sentences were categorized
    if not categorization_result.sentences:
        console.print("[yellow]No sentences to classify, skipping classification step[/yellow]")
        classification_result = ClassificationResult(artefacts=[])
    else:
        # Create a dictionary with categorized sentence details for classification
        categorized_details = {
            s.id: {
                "text": s.text,
                "source": s.source,
                "page": s.page,
                "confidence": s.confidence,
                "category": s.category
            } for s in categorization_result.sentences
        }
        
        classifier = ClassificationAgent(provider=provider, model=model)
        classification_result = classifier.run(categorized_details)
    
    _print_classification(classification_result)

    console.rule("[bold]Inference")
    # Skip inference if no artefacts were classified
    if not classification_result.artefacts:
        console.print("[yellow]No artefacts to infer from, skipping inference step[/yellow]")
        inference_result = InferenceResult(new_artefacts=[], relationships=[])
    else:
        inferencer = InferenceAgent(provider=provider, model=model)
        inference_result = inferencer.run(classification_result.artefacts)
    
    _print_inference(inference_result)

    if output:
        data = {
            "extraction": json.loads(extraction_result.json()),
            "categorization": json.loads(categorization_result.json()),
            "classification": json.loads(classification_result.json()),
            "inference": json.loads(inference_result.json()),
        }
        Path(output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        console.print(f"Saved JSON to {output}")


@app.command("from-csv")
def from_csv(
    input: str = typer.Option(..., help="Path to a CSV of business architecture objects"),
    provider: Optional[str] = typer.Option(None, help="LLM provider: openai|anthropic|azure"),
    model: Optional[str] = typer.Option(None, help="Model or deployment name"),
    output: Optional[str] = typer.Option(None, help="Optional JSON output path"),
):
    """Skip extraction: load structured BA objects and run ontology inference."""
    load_dotenv()

    console.rule("[bold]Loading structured BA objects")
    csv_path = Path(input)
    if not csv_path.exists():
        console.print(f"[red]CSV not found: {csv_path}[/red]")
        raise typer.Exit(code=1)

    try:
        classification_result = classification_from_csv(csv_path)
    except CsvArtefactError as exc:
        console.print(f"[red]Could not load CSV: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    extraction_result = ExtractionResult(sentences=[])
    categorization_result = CategorizationResult(sentences=[])
    _print_classification(classification_result)

    console.rule("[bold]Inference")
    if not classification_result.artefacts:
        console.print("[yellow]No artefacts to infer from, skipping inference step[/yellow]")
        inference_result = InferenceResult(new_artefacts=[], relationships=[])
    else:
        inferencer = InferenceAgent(provider=provider, model=model)
        inference_result = inferencer.run(classification_result.artefacts)

    _print_inference(inference_result)

    if output:
        data = {
            "extraction": json.loads(extraction_result.json()),
            "categorization": json.loads(categorization_result.json()),
            "classification": json.loads(classification_result.json()),
            "inference": json.loads(inference_result.json()),
            "source": "csv",
        }
        Path(output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        console.print(f"Saved JSON to {output}")


if __name__ == "__main__":
    app()

