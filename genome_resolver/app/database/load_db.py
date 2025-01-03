# /database/clinvar_db.py
from cyvcf2 import VCF
import pandas as pd
from .db import get_db

def load_clinvar_vcf(file_path: str):
    clinvar_reader = VCF(file_path)
    clinvar_variants = []
    for variant in clinvar_reader:
        chrom = variant.CHROM
        pos = variant.POS
        ref = variant.REF
        alt = ",".join(variant.ALT)
        clin_sig = variant.INFO.get('CLNSIG', None)
        disease_names = variant.INFO.get('CLNDN')
        gene = variant.INFO.get('GENEINFO', None)
        clinvar_variants.append([chrom, pos, ref, alt, clin_sig, gene, disease_names])
    df_clinvar = pd.DataFrame(clinvar_variants, columns=["CHROM", "POS", "REF", "ALT", "CLNSIG", "GENEINFO", "DISEASE"])
    #with get_db() as conn:
    #    df_clinvar.to_sql('clinvar', conn, if_exists='replace', index=False)
    return df_clinvar
def load_gwas_to_db(file_path: str):
    df_gwas = pd.read_csv(file_path, sep='\t')

    #with get_db() as conn:
    #    df_gwas.to_sql('gwas_catalog', conn, if_exists='replace', index=False)
    return df_gwas