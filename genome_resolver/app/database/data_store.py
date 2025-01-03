
from app.database.load_db import load_clinvar_vcf, load_gwas_to_db


clinvar_df = load_clinvar_vcf("app/database/clinvar_20240917.vcf.gz")
gwas_df = load_gwas_to_db("app/database/gwas_catalog.tsv")