"""
DeepRareAgent Benchmark Script
------------------------------
This script is designed to evaluate the DeepRareAgent against the RareBench dataset.
It mocks the RareBench input format and runs the agent to calculate Top-K accuracy.

Reference: RareBench (NeurIPS 2024), RareAgents (ArXiv 2024)
"""

import argparse
import json
import asyncio
from typing import List, Dict, Any

# Placeholder for future import of the actual agent
# from DeepRareAgent.graph import graph

async def load_rarebench_cases(file_path: str) -> List[Dict[str, Any]]:
    """
    Load RareBench cases from a JSON file.
    Expected format: 
    [
        {
            "case_id": "1",
            "phenotypes": ["HP:000123", "HP:000456"],
            "description": "Patient presents with...",
            "gold_standard_disease": "ORPHA:12345"
        },
        ...
    ]
    """
    # In a real scenario, this would read a file. 
    # For now, we return a mock case.
    mock_case = {
        "case_id": "mock_001",
        "phenotypes": ["HP:0001263", "HP:0000407"],
        "description": "A 5-year-old boy globally delayed in development...",
        "gold_standard_disease": "Angelman syndrome"
    }
    return [mock_case]

async def evaluate_agent(cases: List[Dict[str, Any]]):
    print(f"Starting evaluation on {len(cases)} cases...")
    correct_top1 = 0
    correct_top5 = 0

    for case in cases:
        print(f"Processing Case {case['case_id']}...")
        
        # TODO: Integrate with DeepRareAgent.graph.ainvoke()
        # inputs = {"messages": [HumanMessage(content=case['description'])]}
        # result = await graph.ainvoke(inputs)
        
        # Mock result for now
        predicted_diseases = ["Angelman syndrome", "Prader-Willi syndrome", "Rett syndrome"]
        
        print(f"  Gold Standard: {case['gold_standard_disease']}")
        print(f"  Predictions: {predicted_diseases}")
        
        if case['gold_standard_disease'] == predicted_diseases[0]:
            correct_top1 += 1
        if case['gold_standard_disease'] in predicted_diseases[:5]:
            correct_top5 += 1
            
    print("-" * 30)
    print(f"Top-1 Accuracy: {correct_top1 / len(cases):.2%}")
    print(f"Top-5 Accuracy: {correct_top5 / len(cases):.2%}")

if __name__ == "__main__":
    asyncio.run(evaluate_agent(await load_rarebench_cases("mock.json")))
