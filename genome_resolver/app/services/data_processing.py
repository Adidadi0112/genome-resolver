import pandas as pd
from cyvcf2 import VCF
from ..services.report_generation import generate_report
from ..database.data_store import clinvar_df, gwas_df
import os


def process_vcf_file(file) -> pd.DataFrame:
    vcf_reader = VCF(file.file)
    variants = []
    for record in vcf_reader:
            chrom = record.CHROM
            pos = record.POS
            ref = record.REF
            alt = ",".join(record.ALT)
            qual = record.QUAL
            genotypes = record.genotypes
            variants.append([chrom, pos, ref, alt, qual, genotypes])

    df = pd.DataFrame(variants, columns=["CHROM", "POS", "REF", "ALT", "QUAL", "GENOTYPES"])

    # filter out variants with low QUAL scores
    high_quality_variants = df[df["QUAL"] >= 50]
    # Przekształcenie wartości ALT na listy, jeśli są zapisane jako stringi rozdzielone przecinkami
    high_quality_variants["ALT"] = high_quality_variants["ALT"].apply(lambda x: x.split(",") if isinstance(x, str) else x)

    # Rozdzielenie wartości ALT na osobne wiersze
    high_quality_variants = high_quality_variants.explode("ALT")

    # Zamiana "<NON_REF>" na None
    high_quality_variants["ALT"] = high_quality_variants["ALT"].apply(lambda x: x if x != "<NON_REF>" else None)

    # Usunięcie wierszy, gdzie ALT ma wartość None
    high_quality_variants = high_quality_variants.dropna(subset=["ALT"])

    return high_quality_variants

def perform_full_analysis(combined_variants: pd.DataFrame):
    # Dopasowanie do ClinVar
    merged_clinvar_variants = merge_clinvar_variants(combined_variants, clinvar_df)

    # Dopasowanie do GWAS
    prs_scores = merge_gwas_variants(combined_variants, gwas_df)

    # Upewnienie się, że katalog raportów istnieje
    output_dir = "generated_reports"
    os.makedirs(output_dir, exist_ok=True)

    # Generowanie jednego raportu PDF
    report_path = os.path.join(output_dir, "medical_report.pdf")
    generate_report(merged_clinvar_variants, prs_scores, report_path)
    
    return report_path




def merge_clinvar_variants(patient_df, clinvar_df):
    matched_variants = pd.merge(patient_df, clinvar_df, on=["CHROM", "POS", "REF", "ALT"], how="inner")

    # Upewnienie się, że katalog raportów istnieje
    output_dir = "generated_reports"
    os.makedirs(output_dir, exist_ok=True)

    # Generowanie jednego raportu PDF
    clinvar_path = os.path.join(output_dir, "matched_variants.csv")

    matched_variants.to_csv(clinvar_path, index=False)
    return matched_variants

def merge_gwas_variants(patient_df, gwas_df):
    gwas_filtered = gwas_df[['CHR_ID', 'CHR_POS', 'SNP_ID_CURRENT', 'DISEASE/TRAIT', 'P-VALUE', 'OR or BETA', 'MAPPED_GENE']]
    gwas_filtered = gwas_filtered.rename(columns={"CHR_ID": "CHROM", "CHR_POS": "POS"})

    gwas_filtered["CHROM"] = gwas_filtered["CHROM"].astype(str)
    gwas_filtered["WEIGHT"] = pd.to_numeric(gwas_filtered["OR or BETA"], errors='coerce')
    gwas_filtered["POS"] = pd.to_numeric(gwas_filtered["POS"], errors="coerce").astype("Int64")
    patient_df["POS"] = patient_df["POS"].astype("Int64")

    mean_prs = calculate_mean_prs(gwas_df)
    # change name of the column Weight to mean_prs
    mean_prs = mean_prs.rename("mean_prs")
     
    merged_data = pd.merge(patient_df, gwas_filtered, on=["CHROM", "POS"], how="inner")

    threshold = 5e-8  # Standardowy próg istotności genome-wide
    filtered_data = merged_data[merged_data["P-VALUE"] < threshold]

    ld_blocks = pd.read_csv(
    "app/services/pyrho_EUR_LD_blocks.bed",
    sep="\t",
    header=None,
    names=["chromosome", "start", "end"],
    dtype={"chromosome": str, "start": "Int64", "end": "Int64"},  # Definicja typów
    skiprows=1  # Pominięcie nagłówka
    )
    ld_blocks["chromosome"] = ld_blocks["chromosome"].str.replace("chr", "")  # Usunięcie "chr" z nazwy chromosomu
     
    clumped_snps = clumping_by_ld(filtered_data, ld_blocks)

     
    clumped_snps["allele_count"] = clumped_snps["GENOTYPES"].apply(calculate_allele_count)
    prs_scores = clumped_snps.groupby("DISEASE/TRAIT").apply(calculate_prs_for_trait).reset_index()
    prs_scores.columns = ["DISEASE/TRAIT", "PRS"]

    prs_scores = prs_scores.sort_values(by="PRS", ascending=False)
    prs_scores = prs_scores.merge(mean_prs, left_on="DISEASE/TRAIT", right_index=True, how="inner")
     
    prs_scores = calculate_z_scores(prs_scores)
    prs_scores = classify_risk(prs_scores)

    # Upewnienie się, że katalog raportów istnieje
    output_dir = "generated_reports"
    os.makedirs(output_dir, exist_ok=True)

    # Generowanie jednego raportu PDF
    gwas_path = os.path.join(output_dir, "prs_scores.csv")

    prs_scores.to_csv(gwas_path, index=False)

    return prs_scores

# Funkcja do obliczania liczby alleli ryzyka
def calculate_allele_count(genotype):
    if not genotype or not isinstance(genotype, list) or not isinstance(genotype[0], list):
        return 0  # Jeśli format jest nieprawidłowy lub wartość jest pusta, zwróć 0
    try:
        return genotype[0][0] + genotype[0][1]  # Sumujemy kopie alleli ryzyka
    except IndexError:
        return 0  # Jeśli wystąpi błąd dostępu, zwróć 0 jako wartość domyślną

# Przeprowadzamy analizę PRS, mnożąc wagę przez liczbę alleli ryzyka i sumując dla każdej choroby
def calculate_prs_for_trait(df):
    df = df.dropna(subset=["WEIGHT", "allele_count"])  # Pomijamy rekordy z brakującymi wartościami
    df["WEIGHT"] = pd.to_numeric(df["WEIGHT"], errors='coerce')  # Konwersja na wartości numeryczne
    df["prs_contribution"] = df["WEIGHT"] * df["allele_count"]  # Obliczamy wkład PRS dla każdej pozycji
    return df["prs_contribution"].sum()

def calculate_mean_prs(gwas_data, mean_genotype=1):
    """
    Oblicza średnie PRS na podstawie istotnych SNP z GWAS dla każdej choroby.
    """
    # Filtrowanie SNP po p-value
    threshold = 5e-8
    filtered_gwas_data = gwas_data[gwas_data["P-VALUE"] < threshold]

    # Obliczenie mean_PRS
    filtered_gwas_data["Weight"] = pd.to_numeric(filtered_gwas_data["OR or BETA"], errors="coerce")
    mean_prs = filtered_gwas_data.groupby("DISEASE/TRAIT")["Weight"].sum() * mean_genotype

    return mean_prs

def clumping_by_ld(merged_data, ld_blocks):
    representative_snps = []
    for _, block in ld_blocks.iterrows():
        snps_in_block = merged_data[
            (merged_data["CHROM"] == block["chromosome"]) &
            (merged_data["POS"] >= block["start"]) &
            (merged_data["POS"] <= block["end"])
        ]
        if not snps_in_block.empty:
            representative_snps.append(snps_in_block.loc[snps_in_block["P-VALUE"].idxmin()])
    return pd.DataFrame(representative_snps)

def calculate_z_scores(prs_scores):
    """
    Oblicza z-score na podstawie PRS pacjenta i symulowanych wartości referencyjnych.
    """
    prs_scores["z_score"] = (prs_scores["PRS"] - prs_scores["mean_prs"]) / 0.2
    return prs_scores

def classify_risk(prs_scores):
    """
    Klasyfikuje ryzyko na podstawie z-score.
    """
    def risk_category(z):
        if z > 2:
            return "High Risk"
        elif z < -2:
            return "Low Risk"
        else:
            return "Normal Risk"

    prs_scores["Risk_Category"] = prs_scores["z_score"].apply(risk_category)
    return prs_scores