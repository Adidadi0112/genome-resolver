import pytest
import pandas as pd
from app.services.data_processing import (
    process_vcf_file,
    merge_clinvar_variants,
    merge_gwas_variants,
    calculate_allele_count,
    calculate_prs_for_trait,
    classify_risk,
    calculate_z_scores
)

# Mock danych ClinVar i GWAS
@pytest.fixture
def mock_clinvar_df():
    return pd.DataFrame({
        "CHROM": ["1", "1"],
        "POS": [12345, 54321],
        "REF": ["A", "T"],
        "ALT": ["G", "C"],
        "CLNSIG": ["Pathogenic", "Pathogenic"]
    })

@pytest.fixture
def mock_gwas_df():
    return pd.DataFrame({
        "CHR_ID": ["1", "1"],
        "CHR_POS": [12345, 54321],
        "DISEASE/TRAIT": ["Trait1", "Trait2"],
        "P-VALUE": [1e-8, 1e-7],
        "OR or BETA": [1.5, 2.0],
        "MAPPED_GENE": ["Gene1", "Gene2"]
    })

@pytest.fixture
def mock_vcf_df():
    return pd.DataFrame({
        "CHROM": ["1", "1"],
        "POS": [12345, 54321],
        "REF": ["A", "T"],
        "ALT": ["G", "C"],
        "QUAL": [60, 55],
        "GENOTYPES": [[[1, 1], [0, 1]], [[1, 0], [0, 0]]]
    })

# Test dla process_vcf_file
def test_process_vcf_file(mocker, tmp_path):
    mock_vcf = tmp_path / "test.vcf"
    mock_vcf.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t12345\t.\tA\tG\t60\tPASS\t.\n"
        "1\t54321\t.\tT\tC\t55\tPASS\t.\n"
    )

    mock_vcf_reader = mocker.patch("app.services.data_processing.VCF")
    mock_vcf_reader.return_value = iter([
        mocker.Mock(CHROM="1", POS=12345, REF="A", ALT=["G"], QUAL=60, genotypes=[[1, 0]]),
        mocker.Mock(CHROM="1", POS=54321, REF="T", ALT=["C"], QUAL=55, genotypes=[[0, 1]])
    ])
    
    result = process_vcf_file(mock_vcf)
    assert not result.empty
    assert len(result) == 2
    assert "CHROM" in result.columns

# Test dla merge_clinvar_variants
def test_merge_clinvar_variants(mock_vcf_df, mock_clinvar_df):
    merged = merge_clinvar_variants(mock_vcf_df, mock_clinvar_df)
    assert not merged.empty
    assert len(merged) == 2
    assert "CLNSIG" in merged.columns

# Test dla merge_gwas_variants
def test_merge_gwas_variants(mock_vcf_df, mock_gwas_df):
    merged = merge_gwas_variants(mock_vcf_df, mock_gwas_df)
    assert not merged.empty
    assert "PRS" in merged.columns

# Test dla calculate_allele_count
def test_calculate_allele_count():
    genotype = [[1, 1]]
    assert calculate_allele_count(genotype) == 2

    invalid_genotype = []
    assert calculate_allele_count(invalid_genotype) == 0

# Test dla calculate_prs_for_trait
def test_calculate_prs_for_trait():
    mock_trait_df = pd.DataFrame({
        "WEIGHT": [1.5, 2.0],
        "allele_count": [1, 2]
    })
    result = calculate_prs_for_trait(mock_trait_df)
    assert result == 5.5

# Test dla classify_risk
def test_classify_risk():
    mock_prs_scores = pd.DataFrame({
        "z_score": [3.0, 0.5, -3.0]
    })
    classified = classify_risk(mock_prs_scores)
    assert classified["Risk_Category"].tolist() == ["High Risk", "Normal Risk", "Low Risk"]

# Test dla calculate_z_scores
def test_calculate_z_scores():
    mock_prs_scores = pd.DataFrame({
        "PRS": [2.0, 3.0],
        "mean_prs": [1.0, 2.5]
    })
    z_scores = calculate_z_scores(mock_prs_scores)
    assert "z_score" in z_scores.columns
    assert z_scores["z_score"].tolist() == [5.0, 2.5]
