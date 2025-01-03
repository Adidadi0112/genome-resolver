import pytest
import pandas as pd
from reportlab.platypus import SimpleDocTemplate
from app.services.report_generation import (
    generate_report,
    StyledTile,
    HorizontalTileRow
)

# Mock danych ClinVar i GWAS
@pytest.fixture
def mock_clinvar_df():
    return pd.DataFrame({
        "CHROM": ["1", "2"],
        "POS": [12345, 54321],
        "REF": ["A", "T"],
        "ALT": ["G", "C"],
        "GENEINFO": ["GENE1", "GENE2"],
        "DISEASE": ["Disease1", "Disease2"],
        "CLNSIG": ["Pathogenic", "Likely Pathogenic"],
        "GENOTYPES": ["[[1, 1, False]]", "[[0, 1, False]]"]
    })

@pytest.fixture
def mock_gwas_df():
    return pd.DataFrame({
        "DISEASE/TRAIT": ["Trait1", "Trait2"],
        "PRS": [1.5, 2.0],
        "mean_prs": [1.0, 1.8],
        "z_score": [2.5, 1.5],
        "Risk_Category": ["High Risk", "Normal Risk"]
    })

# Test dla StyledTile
def test_styled_tile_rendering():
    tile = StyledTile(title="Pathogenic", value=10)
    assert tile.title == "Pathogenic"
    assert tile.value == 10
    assert tile.width == 150
    assert tile.height == 80

# Test dla HorizontalTileRow
def test_horizontal_tile_row_rendering():
    tile1 = StyledTile(title="High Risk", value=5)
    tile2 = StyledTile(title="Normal Risk", value=10)
    row = HorizontalTileRow(tiles=[tile1, tile2])
    assert len(row.tiles) == 2
    assert row.total_width == 340  # 150 + 150 + 20 (spacing)

# Test dla generate_report
def test_generate_report(tmp_path, mock_clinvar_df, mock_gwas_df):
    output_file = tmp_path / "test_report.pdf"

    # Generowanie raportu
    generate_report(mock_clinvar_df, mock_gwas_df, str(output_file))

    # Sprawdzenie, czy plik PDF został wygenerowany
    assert output_file.exists()
    assert output_file.stat().st_size > 0