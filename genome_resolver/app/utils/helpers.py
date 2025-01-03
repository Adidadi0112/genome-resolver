import pandas as pd

def dataframe_to_markdown_table(df: pd.DataFrame, columns=None):
    """Converts a DataFrame to a Markdown-style table for LLM prompts."""
    #if columns:
    #   df = df[columns]
    return df.to_markdown(index=False)

def truncate_text(text, max_length=30):
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text
