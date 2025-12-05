def route_from_scores(scores: dict): 
    """
    Determines the target department(s) and priority based on GNN confidence scores.
    """
    
    # Ensure scores are non-empty and convert any potential None values to 0.0 for safety
    if not scores:
        return {"departments": ["Unknown"], "priority": 'low', "scores": {}}

    # Normalize scores to handle potential missing keys if the GNN was trained on a different set
    valid_scores = {d: s if isinstance(s, (int, float)) else 0.0 for d, s in scores.items()}

    # --- 1. Primary Selection: Select departments above the high confidence threshold (0.35) ---
    selected = [d for d, s in valid_scores.items() if s > 0.35]
    
    # --- 2. Fallback Selection: If no strong match found ---
    if not selected:
        # Sort all departments by score, descending
        sorted_depts = sorted(valid_scores.items(), key=lambda kv: kv[1], reverse=True)
        
        # Select the single highest-scoring department as a fallback, if one exists
        if sorted_depts:
            top_dept, top_score = sorted_depts[0]
            selected = [top_dept]
            
            # Optional: Select the second highest if its score is also reasonably high (> 0.1)
            if len(sorted_depts) > 1:
                second_dept, second_score = sorted_depts[1]
                if second_score > 0.1 and (top_score - second_score) < 0.3:
                     selected.append(second_dept)
        else:
            # Should not happen if scores dictionary is non-empty
            selected = ["Unknown"]
    
    # --- 3. Priority Assignment ---
    # Use the max score of the *selected* department(s) to set the priority
    max_score = max([valid_scores.get(d, 0.0) for d in selected]) if selected else 0.0
    
    if max_score > 0.7:
        priority = 'high'
    elif max_score > 0.4:
        priority = 'medium'
    else:
        priority = 'low'

    return {"departments": selected, "priority": priority, "scores": valid_scores}