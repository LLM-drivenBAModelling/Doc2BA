import json
import os
import tempfile
from pathlib import Path
from io import StringIO

import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD

from ba_agents.categorization_agent import CategorizationAgent
from ba_agents.classification_agent import ClassificationAgent
from ba_agents.extraction_agent import ExtractionAgent
from ba_agents.inference_agent import InferenceAgent
from models.schemas import (
    BusinessArtefact,
    CategorizationResult,
    ClassificationResult,
    ExtractionResult,
    InferenceResult,
)
from utils.loaders import DocumentChunk, load_inputs
from utils.graph_visualization import generate_relationship_graph
from config.ba_config import BusinessArtefactType

# Load environment variables
load_dotenv()

# Function to generate TTL from business artifacts
def generate_ttl_from_artifacts(classification_result, inference_result):
    """Generate TTL (Turtle) representation of business architecture artifacts"""
    # Create a new RDF graph (without loading the ontology)
    g = Graph()
    
    # Define namespaces
    BA = Namespace("http://capsifi.com/doc2ba/")
    g.bind("ba", BA)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    
    # Add all classified artifacts
    if classification_result and classification_result.artefacts:
        for artifact in classification_result.artefacts:
            # Create a URI for the artifact instance
            artifact_uri = URIRef(f"{BA}{artifact.id}")
            
            # Add type based on the artifact type
            artifact_type_uri = URIRef(f"{BA}{artifact.type.value}")
            g.add((artifact_uri, RDF.type, artifact_type_uri))
            
            # Add label (name)
            g.add((artifact_uri, RDFS.label, Literal(artifact.name, datatype=XSD.string)))
            
            # Add attributes if any
            if artifact.attributes:
                for key, value in artifact.attributes.items():
                    # Convert attribute key to camelCase for RDF property
                    prop_name = key[0].lower() + key[1:] if key else ""
                    g.add((artifact_uri, URIRef(f"{BA}{prop_name}"), Literal(value, datatype=XSD.string)))
    
    # Add all inferred artifacts
    if inference_result:
        # Add new artifacts
        if inference_result.new_artefacts:
            for artifact in inference_result.new_artefacts:
                # Create a URI for the artifact instance
                artifact_uri = URIRef(f"{BA}{artifact.id}")
                
                # Add type based on the artifact type
                artifact_type_uri = URIRef(f"{BA}{artifact.type.value}")
                g.add((artifact_uri, RDF.type, artifact_type_uri))
                
                # Add label (name)
                g.add((artifact_uri, RDFS.label, Literal(artifact.name, datatype=XSD.string)))
                
                # Add attributes if any
                if artifact.attributes:
                    for key, value in artifact.attributes.items():
                        # Convert attribute key to camelCase for RDF property
                        prop_name = key[0].lower() + key[1:] if key else ""
                        g.add((artifact_uri, URIRef(f"{BA}{prop_name}"), Literal(value, datatype=XSD.string)))
        
        # Add relationships
        if inference_result.relationships:
            for rel in inference_result.relationships:
                source_uri = URIRef(f"{BA}{rel.source_id}")
                target_uri = URIRef(f"{BA}{rel.target_id}")
                rel_type_uri = URIRef(f"{BA}{rel.type}")
                
                # Add the relationship triple
                g.add((source_uri, rel_type_uri, target_uri))
    
    # Serialize the graph to Turtle format as a string (not bytes)
    ttl_data = g.serialize(format="turtle")
    # Handle bytes vs string conversion
    if isinstance(ttl_data, bytes):
        ttl_data = ttl_data.decode('utf-8')
    return ttl_data



# Set page configuration
st.set_page_config(
    page_title="doc2ba: Business Architecture Miner",
    page_icon="📊",
    layout="wide",
)

# App title and description
st.title("doc2ba: Multi-Agent Business Architecture Miner")
st.markdown(
    """
    Extract business architecture components from documents using AI.
    
    **Pipeline stages:**
    1. **Extract** - Find relevant sentences from documents
    2. **Categorize** - Group sentences into high-level categories
    3. **Classify** - Identify specific business artefacts
    4. **Infer** - Discover relationships between artefacts
    """
)

# Sidebar for configuration
st.sidebar.title("Configuration")

# LLM provider selection
provider = st.sidebar.selectbox(
    "LLM Provider",
    options=["openai", "anthropic", "azure"],
    index=0,
    help="Select the LLM provider to use",
)

# Model selection based on provider
default_models = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "azure": "default",
}
model = st.sidebar.text_input("Model Name", value=default_models[provider])

# Session state for storing results
if "extraction_result" not in st.session_state:
    st.session_state.extraction_result = None
if "categorization_result" not in st.session_state:
    st.session_state.categorization_result = None
if "classification_result" not in st.session_state:
    st.session_state.classification_result = None
if "inference_result" not in st.session_state:
    st.session_state.inference_result = None

# File uploader
uploaded_files = st.file_uploader(
    "Upload document files (PDF, TXT, MD)",
    type=["pdf", "txt", "md"],
    accept_multiple_files=True,
)

def process_uploaded_files():
    """Process uploaded files and run the pipeline"""
    if not uploaded_files:
        st.warning("Please upload at least one document file.")
        return
    
    # Save uploaded files to temp directory
    temp_dir = tempfile.mkdtemp()
    file_paths = []
    
    for uploaded_file in uploaded_files:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        file_paths.append(file_path)
    
    # Process files through the pipeline
    with st.spinner("Loading documents..."):
        chunks = load_inputs(temp_dir)
        if not chunks:
            st.error("No supported files could be processed.")
            return
        st.success(f"Loaded {len(chunks)} document chunks")
    
    # Run extraction step
    with st.spinner("Extracting relevant sentences..."):
        extractor = ExtractionAgent(provider=provider, model=model)
        extraction_pairs = extractor.run(chunks)
        
        sentences = []
        for chunk, candidates in extraction_pairs:
            if candidates and hasattr(candidates, 'sentences'):
                for cand in candidates.sentences:
                    sentences.append({
                        "id": f"s-{len(sentences)}",
                        "text": cand.text,
                        "source": chunk.source,
                        "page": chunk.page,
                        "confidence": cand.confidence,
                    })
        
        st.session_state.extraction_result = ExtractionResult(sentences=[
            # type: ignore[arg-type]
            s for s in sentences
        ])
        
    # Run categorization step
    if st.session_state.extraction_result.sentences:
        with st.spinner("Categorizing sentences..."):
            sentence_details = {
                s.id: {
                    "text": s.text,
                    "source": s.source,
                    "page": s.page,
                    "confidence": s.confidence
                } for s in st.session_state.extraction_result.sentences
            }
            
            categorizer = CategorizationAgent(provider=provider, model=model)
            st.session_state.categorization_result = categorizer.run(sentence_details)
    else:
        st.session_state.categorization_result = CategorizationResult(sentences=[])
    
    # Run classification step
    if st.session_state.categorization_result.sentences:
        with st.spinner("Classifying business artefacts..."):
            categorized_details = {
                s.id: {
                    "text": s.text,
                    "source": s.source,
                    "page": s.page,
                    "confidence": s.confidence,
                    "category": s.category
                } for s in st.session_state.categorization_result.sentences
            }
            
            classifier = ClassificationAgent(provider=provider, model=model)
            st.session_state.classification_result = classifier.run(categorized_details)
    else:
        st.session_state.classification_result = ClassificationResult(artefacts=[])
    
    # Run inference step
    if st.session_state.classification_result.artefacts:
        with st.spinner("Inferring relationships..."):
            inferencer = InferenceAgent(provider=provider, model=model)
            st.session_state.inference_result = inferencer.run(st.session_state.classification_result.artefacts)
    else:
        st.session_state.inference_result = InferenceResult(new_artefacts=[], relationships=[])
    
    # Clean up temp directory
    for file_path in file_paths:
        try:
            os.remove(file_path)
        except:
            pass
    try:
        os.rmdir(temp_dir)
    except:
        pass

# Run button
if st.button("Run Analysis"):
    process_uploaded_files()

# Display results
if st.session_state.extraction_result:
    st.header("Analysis Results")
    
    # Create tabs for each pipeline step
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"Extraction ({len(st.session_state.extraction_result.sentences)})", 
        f"Categorization ({len(st.session_state.categorization_result.sentences)})",
        f"Classification ({len(st.session_state.classification_result.artefacts)})",
        "Inference",
        "Relationship Graph"
    ])
    
    # Tab 1: Extraction Results
    with tab1:
        if st.session_state.extraction_result.sentences:
            st.subheader("Extracted Sentences")
            
            # Create DataFrame for display
            extraction_data = []
            for s in st.session_state.extraction_result.sentences:
                extraction_data.append({
                    "ID": s.id,
                    "Source": f"{s.source}:{s.page}" if s.page else s.source,
                    "Confidence": f"{s.confidence:.2f}",
                    "Text": s.text[:100] + ("..." if len(s.text) > 100 else "")
                })
                
            st.dataframe(extraction_data, use_container_width=True)
        else:
            st.info("No sentences were extracted.")
    
    # Tab 2: Categorization Results
    with tab2:
        if st.session_state.categorization_result.sentences:
            st.subheader("Categorized Sentences")
            
            # Create DataFrame for display
            categorization_data = []
            for s in st.session_state.categorization_result.sentences:
                categorization_data.append({
                    "ID": s.id,
                    "Source": f"{s.source}:{s.page}" if s.page else s.source,
                    "Category": s.category.value,
                    "Cat. Conf": f"{s.category_confidence:.2f}",
                    "Text": s.text[:100] + ("..." if len(s.text) > 100 else "")
                })
                
            st.dataframe(categorization_data, use_container_width=True)
            
            # Add category distribution chart
            categories = {}
            for s in st.session_state.categorization_result.sentences:
                cat = s.category.value
                if cat in categories:
                    categories[cat] += 1
                else:
                    categories[cat] = 1
            
            fig = go.Figure(data=[go.Pie(
                labels=list(categories.keys()),
                values=list(categories.values()),
                hole=.3,
                marker_colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA']
            )])
            fig.update_layout(title_text="Category Distribution")
            st.plotly_chart(fig)
        else:
            st.info("No sentences were categorized.")
    
    # Tab 3: Classification Results
    with tab3:
        if st.session_state.classification_result.artefacts:
            st.subheader("Classified Artefacts")
            
            # Create DataFrame for display
            classification_data = []
            for a in st.session_state.classification_result.artefacts:
                classification_data.append({
                    "ID": a.id,
                    "Type": a.type.value,
                    "Confidence": f"{a.confidence:.2f}",
                    "Name": a.name
                })
                
            st.dataframe(classification_data, use_container_width=True)
            
            # Add artefact type distribution chart
            artefact_types = {}
            for a in st.session_state.classification_result.artefacts:
                typ = a.type.value
                if typ in artefact_types:
                    artefact_types[typ] += 1
                else:
                    artefact_types[typ] = 1
            
            fig = go.Figure(data=[go.Bar(
                x=list(artefact_types.keys()),
                y=list(artefact_types.values())
            )])
            fig.update_layout(title_text="Artefact Types Distribution")
            st.plotly_chart(fig)
        else:
            st.info("No artefacts were classified.")
    
    # Tab 4: Inference Results
    with tab4:
        if st.session_state.inference_result.relationships or st.session_state.inference_result.new_artefacts:
            # Show new artefacts if any
            if st.session_state.inference_result.new_artefacts:
                st.subheader("Inferred Artefacts")
                
                # Create DataFrame for display
                inferred_artefacts_data = []
                for a in st.session_state.inference_result.new_artefacts:
                    inferred_artefacts_data.append({
                        "ID": a.id,
                        "Type": a.type.value,
                        "Confidence": f"{a.confidence:.2f}",
                        "Name": a.name
                    })
                    
                st.dataframe(inferred_artefacts_data, use_container_width=True)
            
            # Show relationships
            if st.session_state.inference_result.relationships:
                st.subheader("Inferred Relationships")
                
                # Create DataFrame for display
                relationship_data = []
                for r in st.session_state.inference_result.relationships:
                    relationship_data.append({
                        "Source ID": r.source_id,
                        "Relationship": r.type,
                        "Target ID": r.target_id,
                        "Confidence": f"{r.confidence:.2f}"
                    })
                    
                st.dataframe(relationship_data, use_container_width=True)
                
                # Add relationship type distribution chart
                rel_types = {}
                for r in st.session_state.inference_result.relationships:
                    rel = r.type
                    if rel in rel_types:
                        rel_types[rel] += 1
                    else:
                        rel_types[rel] = 1
                
                fig = go.Figure(data=[go.Bar(
                    x=list(rel_types.keys()),
                    y=list(rel_types.values())
                )])
                fig.update_layout(title_text="Relationship Types Distribution")
                st.plotly_chart(fig)
        else:
            st.info("No relationships or new artefacts were inferred.")
    
    # Tab 5: Relationship Graph
    with tab5:
        if (st.session_state.classification_result.artefacts or 
            (st.session_state.inference_result and st.session_state.inference_result.relationships)):
            st.subheader("Business Architecture Relationship Graph")
            
            # Generate the graph visualization
            fig = generate_relationship_graph(
                st.session_state.classification_result,
                st.session_state.inference_result
            )
            
            # Display the graph with more height
            st.plotly_chart(fig, use_container_width=True, height=700)
            
            st.write("""
            This graph visualizes the relationships between business architecture artifacts.
            - Node colors represent different artifact types
            - Node size reflects confidence level in the artifact
            - Edge width represents confidence level in the relationship
            - Hover over nodes and edges for detailed information
            """)
            
            # Add filter options for the graph
            st.write("### Graph Filters")
            st.write("Coming soon: Ability to filter by artifact type, relationship type, and confidence level")
            
        else:
            st.info("No artifacts or relationships available for visualization.")
    
    # Add export option
    if (st.session_state.extraction_result.sentences or 
        st.session_state.categorization_result.sentences or 
        st.session_state.classification_result.artefacts or 
        st.session_state.inference_result.relationships):
        
        st.header("Export Results")
        
        export_data = {
            "extraction": json.loads(st.session_state.extraction_result.json()),
            "categorization": json.loads(st.session_state.categorization_result.json()),
            "classification": json.loads(st.session_state.classification_result.json()),
            "inference": json.loads(st.session_state.inference_result.json()),
        }
        
        col1, col2 = st.columns(2)
        
        # Create download button for JSON
        with col1:
            st.download_button(
                label="Download Results as JSON",
                data=json.dumps(export_data, indent=2),
                file_name="doc2ba_results.json",
                mime="application/json"
            )
        
        # Create download button for TTL (only if we have artifacts)
        with col2:
            if st.session_state.classification_result.artefacts or (
                st.session_state.inference_result and (
                    st.session_state.inference_result.new_artefacts or 
                    st.session_state.inference_result.relationships
                )
            ):
                # Generate TTL from artifacts
                ttl_data = generate_ttl_from_artifacts(
                    st.session_state.classification_result, 
                    st.session_state.inference_result
                )
                
                st.download_button(
                    label="Download Business Architecture as TTL",
                    data=ttl_data,
                    file_name="business_architecture.ttl",
                    mime="text/turtle"
                )
            else:
                st.button("Download Business Architecture as TTL", disabled=True,
                          help="No business architecture artifacts to export")

# Footer
st.markdown("---")
st.markdown("doc2ba: Multi-Agent Business Architecture Miner - Experimental Project")
