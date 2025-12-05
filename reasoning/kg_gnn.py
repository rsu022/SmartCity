# reasoning/kg_gnn.py
"""
Knowledge-Graph + lightweight GNN-based department classifier.
Used AFTER YOLO detection to determine responsible department.
"""

import networkx as nx
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


DEPARTMENTS = [
    "Waste Management",
    "Construction",
    "Municipality",
    "Roads",
    "Electricity",
    "Water",
    "Ward Office"
]


class SimpleGNN(nn.Module):
    def __init__(self, in_dim, hidden_dim, out_dim):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden_dim)
        self.fc_msg = nn.Linear(hidden_dim, hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, out_dim)

    def forward(self, features, adj, steps=2):
        # Initial transformation
        h = F.relu(self.fc1(features))
        
        # Message Passing (Graph Convolution equivalent for 2 steps)
        for _ in range(steps):
            # Message aggregation: m = A * h
            m = torch.matmul(adj, h)
            # Message update
            h = F.relu(self.fc_msg(m))
            
        # Output layer with Sigmoid for multi-label confidence/scores
        return torch.sigmoid(self.fc_out(h))


class KnowledgeGraphReasoner:
    def __init__(self):
        self.G = nx.DiGraph()

        # Department nodes
        for d in DEPARTMENTS:
            self.G.add_node(d, type='dept')

        # Attribute nodes
        self.attrs = [
            "large_waste", "hazardous_waste",
            "large_pothole", "deep_pothole",
            "near_electric", "near_water"
        ]

        for a in self.attrs:
            self.G.add_node(a, type='attr')

        # Logical edges (Attribute -> Department)
        edges = [
            ("large_waste", "Waste Management"),
            ("hazardous_waste", "Waste Management"),
            ("large_waste", "Ward Office"), # Local management often handles large objects
            ("deep_pothole", "Roads"),
            ("large_pothole", "Roads"),
            ("near_electric", "Electricity"),
            ("near_water", "Water")
        ]

        for u, v in edges:
            self.G.add_edge(u, v)

        self.nodes = list(self.G.nodes())
        self.node_index = {n: i for i, n in enumerate(self.nodes)}

        self.in_dim = 8
        self.hidden_dim = 16
        self.out_dim = len(DEPARTMENTS)
        
        # Initialize model (can load pre-trained weights here if available)
        self.model = SimpleGNN(self.in_dim, self.hidden_dim, self.out_dim)

    # ---------------------------
    # FEATURE MATRIX (X)
    # ---------------------------
    def build_feature_matrix(self, detection):
        N = len(self.nodes)
        feats = np.zeros((N, self.in_dim), dtype=np.float32)

        params = detection.get("params", {})
        t = detection.get("type")

        # Trigger map
        attr_map = {a: False for a in self.attrs}

        # ---- Waste logic ----
        if t == "waste":
            p = params.get("primary", {})
            if p:
                if p.get("area_pct", 0) > 0.02:
                    attr_map["large_waste"] = True

                cls = p.get("class_name", "").lower()
                if "battery" in cls or "chemical" in cls:
                    attr_map["hazardous_waste"] = True

        # ---- Pothole logic ----
        # FIX: Corrected typo 'pothhole' to 'pothole'
        if t == "pothole": 
            p = params.get("primary", {})
            if p:
                if p.get("area_pct", 0) > 0.01:
                    attr_map["large_pothole"] = True
                if p.get("est_depth_m", 0) > 0.05:
                    attr_map["deep_pothole"] = True

        # Apply attribute features (Binary activation features)
        for a in self.attrs:
            idx = self.node_index[a]
            val = 1.0 if attr_map[a] else 0.0
            feats[idx, 0] = val
            feats[idx, 1] = val # Duplicating features slightly increases the input dimension size

        # Dept priors (Weak prior signal for each department node)
        for i, d in enumerate(DEPARTMENTS):
            idx = self.node_index[d]
            # Use index 2 for a generic department prior feature
            feats[idx, 2] = 0.1 

        return torch.from_numpy(feats)

    # ---------------------------
    # ADJACENCY MATRIX (A)
    # ---------------------------
    def build_adj_matrix(self):
        N = len(self.nodes)
        adj = np.zeros((N, N), dtype=np.float32)

        # Build unnormalized symmetric adjacency matrix (A)
        for u, v in self.G.edges():
            ui, vi = self.node_index[u], self.node_index[v]
            adj[ui, vi] = 1 # Directed edge (for attribute -> dept)
            adj[vi, ui] = 1 # Undirected for message passing (dept -> attribute)

        # Add self-loops (required for GNN message passing)
        for i in range(N):
            adj[i, i] = 1

        # Normalize A: Row-normalize to get D^-1 A or similar (sum(row) = 1)
        # This is a simple normalization used in some GNN variants.
        # Note: A proper GCN uses a symmetric normalization D^-0.5 A D^-0.5
        adj_sum = adj.sum(axis=1, keepdims=True)
        # Handle division by zero for isolated nodes (though none exist here)
        adj_sum[adj_sum == 0] = 1 
        adj = adj / adj_sum
        
        return torch.from_numpy(adj)

    # ---------------------------
    # FINAL REASONING
    # ---------------------------
    def reason(self, detection_record):
        feat = self.build_feature_matrix(detection_record)
        adj = self.build_adj_matrix()

        with torch.no_grad():
            out = self.model(feat, adj)
            
            # Extract scores for only the department nodes
            dept_scores_tensor = out[[self.node_index[d] for d in DEPARTMENTS]]
            
            # Sum/Average the scores for the department nodes to get the final confidence
            # Summing the node outputs is a simple way to aggregate the result
            # Assuming the model is designed to make the department node scores meaningful
            final_scores = dept_scores_tensor.sum(dim=0).numpy()


        # Normalization (Min-Max scaling for scores 0 to 1)
        total = final_scores
        total_min, total_max = total.min(), total.max()
        
        if total_max == total_min:
             # If all scores are equal (e.g., all 0.0), return equal scores
             normalized_scores = np.ones_like(total) / len(DEPARTMENTS)
        else:
             normalized_scores = (total - total_min) / (total_max - total_min)
        
        return {dept: float(normalized_scores[i]) for i, dept in enumerate(DEPARTMENTS)}