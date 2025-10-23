from __future__ import annotations

import os
import logging
import importlib.util
from dataclasses import dataclass
from typing import Iterable, List, Optional

from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader, 
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Check which PDF loaders are available
UNSTRUCTURED_AVAILABLE = importlib.util.find_spec("unstructured") is not None
PDFMINER_AVAILABLE = importlib.util.find_spec("pdfminer") is not None

# Only import if available
if UNSTRUCTURED_AVAILABLE:
    from langchain_community.document_loaders import UnstructuredPDFLoader
if PDFMINER_AVAILABLE:
    from langchain_community.document_loaders import PDFMinerLoader


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    source: str
    page: int
    text: str


def _load_pdf(path: str) -> List[DocumentChunk]:
    """Load PDF using multiple strategies for better extraction quality.
    
    Tries multiple loaders in sequence, preferring ones with better extraction.
    """
    chunks: List[DocumentChunk] = []
    source = os.path.basename(path)
    
    # Try UnstructuredPDFLoader first (best quality but needs dependencies)
    if UNSTRUCTURED_AVAILABLE:
        try:
            logger.info(f"Loading PDF with UnstructuredPDFLoader: {path}")
            loader = UnstructuredPDFLoader(path, mode="elements")
            docs = loader.load()
            
            # Group by page
            page_content = {}
            for doc in docs:
                page_num = doc.metadata.get("page_number", 1)
                if page_num not in page_content:
                    page_content[page_num] = []
                page_content[page_num].append(doc.page_content)
            
            # Create chunks from grouped content
            for page_num, contents in page_content.items():
                text = "\n".join(contents)
                if text.strip():
                    chunks.append(DocumentChunk(source=source, page=page_num, text=text))
            
            if chunks:
                logger.info(f"Successfully extracted {len(chunks)} pages with UnstructuredPDFLoader")
                return chunks
        except Exception as e:
            logger.warning(f"UnstructuredPDFLoader failed: {str(e)}")
    else:
        logger.info("UnstructuredPDFLoader not available, skipping")
    
    # Fallback to PDFMinerLoader
    if PDFMINER_AVAILABLE:
        try:
            logger.info(f"Falling back to PDFMinerLoader: {path}")
            loader = PDFMinerLoader(path)
            docs = loader.load()
            
            # PDFMinerLoader typically returns one document with all content
            # We need to split it by page markers if possible
            if docs and docs[0].page_content:
                text = docs[0].page_content
                # Simple heuristic: assume "Page X" markers
                import re
                pages = re.split(r'Page \d+', text)
                if len(pages) > 1:
                    # First element is empty if text starts with "Page X"
                    if not pages[0].strip():
                        pages.pop(0)
                    
                    for i, page_text in enumerate(pages, start=1):
                        if page_text.strip():
                            chunks.append(DocumentChunk(source=source, page=i, text=page_text))
                else:
                    # No page markers, treat as single page
                    chunks.append(DocumentChunk(source=source, page=1, text=text))
                    
            if chunks:
                logger.info(f"Successfully extracted {len(chunks)} pages with PDFMinerLoader")
                return chunks
        except Exception as e:
            logger.warning(f"PDFMinerLoader failed: {str(e)}")
    else:
        logger.info("PDFMinerLoader not available, skipping")
    
    # Last resort: PyPDFLoader
    try:
        logger.info(f"Falling back to PyPDFLoader: {path}")
        loader = PyPDFLoader(path)
        docs = loader.load()
        
        for doc in docs:
            page_num = doc.metadata.get("page", 0) + 1  # LangChain is 0-indexed
            if doc.page_content.strip():
                chunks.append(DocumentChunk(source=source, page=page_num, text=doc.page_content))
        
        logger.info(f"Successfully extracted {len(chunks)} pages with PyPDFLoader")
    except Exception as e:
        logger.warning(f"PyPDFLoader failed: {str(e)}")
    
    return chunks


def _load_text(path: str) -> List[DocumentChunk]:
    """Load text files using LangChain's TextLoader."""
    loader = TextLoader(path, encoding="utf-8")
    docs = loader.load()
    
    return [DocumentChunk(
        source=os.path.basename(path),
        page=1,
        text=doc.page_content
    ) for doc in docs if doc.page_content.strip()]


def load_inputs(input_path: str) -> List[DocumentChunk]:
    """Load PDFs and text files from a file or directory path."""
    paths: List[str] = []
    if os.path.isdir(input_path):
        for root, _dirs, files in os.walk(input_path):
            for name in files:
                if name.lower().endswith((".pdf", ".txt", ".md")):
                    paths.append(os.path.join(root, name))
    else:
        paths.append(input_path)

    chunks: List[DocumentChunk] = []
    for path in paths:
        lower = path.lower()
        if lower.endswith(".pdf"):
            chunks.extend(_load_pdf(path))
        elif lower.endswith(('.txt', '.md')):
            chunks.extend(_load_text(path))
    return chunks

