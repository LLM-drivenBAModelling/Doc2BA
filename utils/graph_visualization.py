"""
Utilities for visualizing business architecture artifacts and relationships as network graphs.
"""

import hashlib
import plotly.graph_objects as go
import networkx as nx

def generate_relationship_graph(classification_result, inference_result):
    """
    Generate a network graph visualization of business artifacts and their relationships.
    
    Args:
        classification_result: ClassificationResult containing business artifacts
        inference_result: InferenceResult containing relationships and additional artifacts
        
    Returns:
        A Plotly figure object with the network graph visualization
    """
    # Create a NetworkX graph
    G = nx.DiGraph()
    
    # Collect all artifacts (both classified and inferred)
    all_artifacts = {}
    
    # Add classified artifacts
    if classification_result and classification_result.artefacts:
        for artifact in classification_result.artefacts:
            all_artifacts[artifact.id] = artifact
    
    # Add inferred artifacts
    if inference_result and inference_result.new_artefacts:
        for artifact in inference_result.new_artefacts:
            all_artifacts[artifact.id] = artifact
    
    # Add nodes to the graph
    node_colors = []
    node_sizes = []
    node_hover_texts = []
    
    # Track unique artifact types to generate colors
    artifact_type_colors = {}
    
    for artifact_id, artifact in all_artifacts.items():
        # Add node
        G.add_node(artifact_id)
        
        # Get color based on artifact type (dynamically generated)
        artifact_type = artifact.type.value
        if artifact_type not in artifact_type_colors:
            # Generate a color based on the hash of the artifact type name
            hash_obj = hashlib.md5(artifact_type.encode())
            hash_int = int(hash_obj.hexdigest(), 16)
            artifact_type_colors[artifact_type] = f"#{hash_int % 0xFFFFFF:06x}"
        
        node_color = artifact_type_colors[artifact_type]
        node_colors.append(node_color)
        
        # Use confidence as node size (scaled)
        node_size = 15 + (artifact.confidence * 15)
        node_sizes.append(node_size)
        
        # Create hover text
        hover_text = f"ID: {artifact.id}<br>Name: {artifact.name}<br>Type: {artifact.type.value}<br>Confidence: {artifact.confidence:.2f}"
        if artifact.attributes:
            hover_text += "<br>Attributes:<br>" + "<br>".join([f"- {k}: {v}" for k, v in artifact.attributes.items()])
        node_hover_texts.append(hover_text)
    
    # Add edges to the graph
    edge_colors = []
    edge_widths = []
    edge_hover_texts = []
    
    # Track unique relationship types to generate colors
    rel_type_colors = {}
    
    if inference_result and inference_result.relationships:
        for rel in inference_result.relationships:
            # Only add edge if both source and target nodes exist
            if rel.source_id in all_artifacts and rel.target_id in all_artifacts:
                # Add edge
                G.add_edge(rel.source_id, rel.target_id)
                
                # Use confidence as edge width
                edge_width = 1 + (rel.confidence * 3)
                edge_widths.append(edge_width)
                
                # Edge color based on relationship type
                rel_type = rel.type
                if rel_type not in rel_type_colors:
                    # Generate a color based on the hash of the relationship type
                    hash_obj = hashlib.md5(rel_type.encode())
                    hash_int = int(hash_obj.hexdigest(), 16)
                    rel_type_colors[rel_type] = f"#{hash_int % 0xFFFFFF:06x}"
                
                edge_color = rel_type_colors[rel_type]
                edge_colors.append(edge_color)
                
                # Create hover text with relationship name prominent
                source_name = all_artifacts[rel.source_id].name
                target_name = all_artifacts[rel.target_id].name
                hover_text = f"<b>Relationship: {rel.type}</b><br>{source_name} → {target_name}<br>Confidence: {rel.confidence:.2f}"
                edge_hover_texts.append(hover_text)
    
    # Create positions for nodes using a spring layout
    pos = nx.spring_layout(G, k=0.8, iterations=100)
    
    # Convert to format expected by Plotly
    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
    
    # Create node trace
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=False,
            color=node_colors,
            size=node_sizes,
            line=dict(width=1, color='#888'),
        ),
        text=node_hover_texts,
        hovertemplate='%{text}<extra></extra>'
    )
    
    # Create edge traces
    edge_traces = []
    i = 0
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        
        if i < len(edge_colors) and i < len(edge_widths) and i < len(edge_hover_texts):
            edge_trace = go.Scatter(
                x=[x0, x1, None], y=[y0, y1, None],
                line=dict(width=edge_widths[i], color=edge_colors[i]),
                hoverinfo='text',
                text=edge_hover_texts[i],
                hovertemplate='%{text}<extra></extra>',
                mode='lines'
            )
            edge_traces.append(edge_trace)
        i += 1
    
    # Create node label trace
    node_label_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='text',
        text=[all_artifacts[node_id].name for node_id in G.nodes()],
        textposition='bottom center',
        textfont=dict(
            family='Arial',
            size=10,
            color='black'
        )
    )
    
    # Create figure with appropriate margins for legend
    fig = go.Figure(layout=go.Layout(
        showlegend=True,  # Using built-in legend instead of annotations
        hovermode='closest',
        margin=dict(b=20, l=20, r=150, t=40),  # Added more right margin for legend
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        title='Business Architecture Relationship Graph',
        annotations=[
            dict(
                text="Node size = confidence<br>Edge width = relationship confidence",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.01, y=0.01
            )
        ],
        legend=dict(
            x=1.02,
            y=0.98,
            xanchor='left',
            yanchor='top',
            bordercolor='#E2E2E2',
            borderwidth=1,
            font=dict(size=10),
        )
    ))
    
    # Add traces with names for the legend
    # First add the artifact type dummy traces for legend
    for artifact_type, color in artifact_type_colors.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=10, color=color),
            name=artifact_type,
            legendgroup='artifact_types',
            showlegend=True
        ))
    
    # Then add relationship type dummy traces for legend if any
    if rel_type_colors:
        # Add a section header for relationships
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),  # Transparent line
            name='<b>Relationship Types:</b>',
            legendgroup='relationships',
            showlegend=True
        ))
        
        for rel_type, color in rel_type_colors.items():
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='lines',
                line=dict(color=color, width=3),
                name=rel_type,
                legendgroup='relationships',
                showlegend=True
            ))
    
    # Add the actual graph traces but hide them from the legend
    for edge_trace in edge_traces:
        edge_trace.showlegend = False  # Don't show in legend
        fig.add_trace(edge_trace)
    
    # Add node traces but hide from legend
    node_trace.showlegend = False
    fig.add_trace(node_trace)
    
    node_label_trace.showlegend = False
    fig.add_trace(node_label_trace)
    
    return fig
