from typing import List
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from ..services.text_generation import (
    generate_summary_text,
    generate_test
)
from ..database.data_store import clinvar_df, gwas_df
from ..services.data_processing import perform_full_analysis, process_vcf_file, merge_clinvar_variants, merge_gwas_variants

router = APIRouter()

@router.post("/generate-summary")
async def summary_endpoint():
    return generate_summary_text(gwas_df, clinvar_df)

@router.post("/merge-clinvar-variants")
async def merge_clinvar_variants_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith(".vcf") and not file.filename.endswith(".vcf.gz"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a VCF file.")
    
    patient_df = process_vcf_file(file)
    matched_variants = merge_clinvar_variants(patient_df, clinvar_df)
    
    return {"message": "ClinVar variants merged successfully.", "data": matched_variants.head().to_dict()}

@router.post("/merge-gwas-variants")
async def merge_gwas_variants_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith(".vcf") and not file.filename.endswith(".vcf.gz"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a VCF file.")
    
    patient_df = process_vcf_file(file)
    prs_scores = merge_gwas_variants(patient_df, gwas_df)
    
    return {"message": "GWAS variants merged successfully.", "data": prs_scores.head().to_dict()}

@router.get("/test_llm")
async def test_llm(input_text: str):
    return generate_test(input_text)

@router.post("/upload-vcfs")
async def upload_vcfs(files: List[UploadFile] = File(...)):
    processed_files = []

    for file in files:
        # Sprawdzanie rozszerzenia pliku
        if not file.filename.endswith(".vcf") and not file.filename.endswith(".vcf.gz"):
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}. Please upload VCF files.")
        
        try:
            # Przetwarzanie każdego pliku VCF
            vcf_df = process_vcf_file(file)
            if vcf_df is None:
                raise HTTPException(status_code=500, detail=f"Failed to process VCF file: {file.filename}.")
            
            # Dodanie przetworzonych danych do listy
            processed_files.append({
                "filename": file.filename,
                "data": vcf_df.head().to_dict()  # Przykład: zwracamy pierwsze kilka wierszy jako podgląd
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while processing file {file.filename}: {str(e)}")

    return {"message": "VCF files processed successfully.", "processed_files": processed_files}


@router.post("/generate-report")
async def generate_health_report(files: List[UploadFile] = File(...)):
    # Sprawdzanie każdego pliku
    for file in files:
        if not file.filename.endswith(".vcf") and not file.filename.endswith(".vcf.gz"):
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}. Please upload VCF files.")

    # Przetwarzanie plików i łączenie wyników w jeden DataFrame
    all_variants = []
    for file in files:
        patient_df = process_vcf_file(file)
        all_variants.append(patient_df)

    # Łączenie wszystkich DataFrame w jeden
    combined_df = pd.concat(all_variants, ignore_index=True)

    # Przeprowadzenie analizy i wygenerowanie jednego raportu PDF
    report_path = perform_full_analysis(combined_df)
    if not report_path:
        raise HTTPException(status_code=500, detail="Failed to generate the report.")
    
    return FileResponse(report_path, media_type="application/pdf", filename="medical_report.pdf")

