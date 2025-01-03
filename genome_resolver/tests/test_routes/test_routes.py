import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

# Test dla /generate-summary
def test_generate_summary(mocker):
    mocker.patch(
        "app.services.text_generation.generate_summary_text",
        return_value="Mocked summary response"
    )
    response = client.post("/generate-summary")
    assert response.status_code == 200
    assert response.json() == "Mocked summary response"

# Test dla /merge-clinvar-variants z poprawnym plikiem
def test_merge_clinvar_variants_valid_file(mocker, tmp_path):
    mock_vcf = tmp_path / "test.vcf"
    mock_vcf.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t12345\t.\tA\tG\t60\tPASS\t.\n"
    )

    mocker.patch("app.services.data_processing.process_vcf_file", return_value={"mock": "data"})
    mocker.patch("app.services.data_processing.merge_clinvar_variants", return_value={"Mocked": "DATA"})

    with open(mock_vcf, "rb") as file:
        response = client.post(
            "/merge-clinvar-variants",
            files={"file": ("test.vcf", file, "application/octet-stream")}
        )
    assert response.status_code == 200
    assert "message" in response.json()
    assert "data" in response.json()

# Test dla /merge-gwas-variants z poprawnym plikiem
def test_merge_gwas_variants_valid_file(mocker, tmp_path):
    mock_vcf = tmp_path / "test.vcf"
    mock_vcf.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t12345\t.\tA\tG\t60\tPASS\t.\n"
    )

    mocker.patch("app.services.data_processing.process_vcf_file", return_value={"mock": "data"})
    mocker.patch("app.services.data_processing.merge_gwas_variants", return_value={"Mocked": "DATA"})

    with open(mock_vcf, "rb") as file:
        response = client.post(
            "/merge-gwas-variants",
            files={"file": ("test.vcf", file, "application/octet-stream")}
        )
    assert response.status_code == 200
    assert "message" in response.json()
    assert "data" in response.json()

# Test dla /test_llm
def test_test_llm(mocker):
    mocker.patch(
        "app.services.text_generation.generate_test",
        return_value={"response": "Mocked LLM response"}
    )
    response = client.get("/test_llm?input_text=Test input")
    assert response.status_code == 200
    assert response.json()["response"] == "Mocked LLM response"

# Test dla /upload-vcfs z poprawnym plikiem
def test_upload_vcfs_valid_file(mocker, tmp_path):
    mock_vcf = tmp_path / "test.vcf"
    mock_vcf.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t12345\t.\tA\tG\t60\tPASS\t.\n"
    )

    mocker.patch("app.services.data_processing.process_vcf_file", return_value={"mock": "data"})

    with open(mock_vcf, "rb") as file:
        response = client.post(
            "/upload-vcfs",
            files={"files": ("test.vcf", file, "application/octet-stream")}
        )
    assert response.status_code == 200
    assert "message" in response.json()
    assert "processed_files" in response.json()

# Test dla /generate-report z poprawnymi plikami
def test_generate_health_report_valid_files(mocker, tmp_path):
    mock_vcf = tmp_path / "test.vcf"
    mock_vcf.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t12345\t.\tA\tG\t60\tPASS\t.\n"
    )

    mocker.patch("app.services.data_processing.process_vcf_file", return_value={"mock": "data"})
    mocker.patch("app.services.data_processing.perform_full_analysis", return_value="mocked_report_path.pdf")

    with open(mock_vcf, "rb") as file:
        response = client.post(
            "/generate-report",
            files={"files": ("test.vcf", file, "application/octet-stream")}
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
