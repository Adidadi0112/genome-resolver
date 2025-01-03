import ollama
from ..utils.helpers import dataframe_to_markdown_table
import pandas as pd

def generate_summary_text(high_risks, pathologies):
    print(high_risks)
    print(pathologies)
    
    prompt = (
        "Create short, detailed, and simple prevention actions for the following diseases:\n\n"
        "High-risk diseases from GWAS:\n{high_risks}\n\n"
        "Pathologies from ClinVar:\n{pathologies}"
        "Don't include sources of information, just the prevention actions."
    ).format(high_risks=high_risks, pathologies=pathologies)

    response = ollama.generate(model="monotykamary/medichat-llama3:latest", prompt=prompt)
    print(response["response"])
    return response["response"]

def generate_test(text_input):
    prompt = text_input
    response = ollama.generate(model="monotykamary/medichat-llama3:latest", prompt=prompt)
    print(response["response"])
    return response

