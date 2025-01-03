from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable, Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
import os

from ..utils.helpers import truncate_text
from ..services.text_generation import (
    generate_summary_text,
)

# Rejestracja niestandardowej czcionki
try:
    pdfmetrics.registerFont(TTFont("DINCondensed", "app/services/DIN-Light.ttf"))
except FileNotFoundError:
    print("DIN-Light.ttf not found. Ensure the file exists at the specified path.")
    raise

class StyledTile(Flowable):
    def __init__(self, title, value, width=150, height=80, background_color="#356774", text_color="#edf6f9"):
        Flowable.__init__(self)
        self.title = title
        self.value = value
        self.width = width
        self.height = height
        self.background_color = HexColor(background_color)
        self.text_color = HexColor(text_color)

    def draw(self):
        canvas = self.canv
        canvas.setFillColor(self.background_color)
        canvas.roundRect(0, 0, self.width, self.height, 10, fill=True, stroke=False)
        canvas.setFillColor(self.text_color)
        canvas.setFont("DINCondensed", 12)
        canvas.drawCentredString(self.width / 2, self.height - 20, self.title)
        canvas.setFont("DINCondensed", 16)
        canvas.drawCentredString(self.width / 2, self.height / 2 - 10, str(self.value))

class HorizontalTileRow(Flowable):
    def __init__(self, tiles, spacing=20):
        Flowable.__init__(self)
        self.tiles = tiles
        self.spacing = spacing
        self.total_width = sum(tile.width for tile in tiles) + (len(tiles) - 1) * spacing
        self.height = max(tile.height for tile in tiles)

    def draw(self):
        canvas = self.canv
        x_offset = 0
        for tile in self.tiles:
            canvas.saveState()
            canvas.translate(x_offset, 0)
            tile.drawOn(canvas, 0, 0)
            canvas.restoreState()
            x_offset += tile.width + self.spacing

def draw_background_on_page(c):
    """Rysowanie tła na każdej stronie."""
    c.setFillColor(HexColor("#83c5be"))
    c.rect(0, 0, letter[0], letter[1], stroke=0, fill=1)

def generate_report(clinvar_df, gwas_df, output_file):
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    styles = getSampleStyleSheet()

    # Style dla raportu
    title_style = ParagraphStyle(
        name="Title",
        fontName="DINCondensed",
        fontSize=24,
        spaceAfter=20,
        textColor=HexColor("#356774"),
    )
    section_title_style = ParagraphStyle(
        name="Heading2",
        fontName="DINCondensed",
        fontSize=18,
        spaceAfter=10,
        textColor=HexColor("#356774"),
    )
    text_style = ParagraphStyle(
        name="BodyText",
        fontName="DINCondensed",
        fontSize=12,
        leading=15,
        textColor=HexColor("#edf6f9"),
    )

    elements = []

    # Tytuł
    elements.append(Paragraph("Genome Overview", title_style))
    elements.append(Spacer(1, 20))

    # Sekcja ClinVar
    elements.append(Paragraph("ClinVar Section", section_title_style))
    elements.append(Spacer(1, 10))

    # Filtracja wariantów ClinVar
    filtered_clinvar_df = clinvar_df[
        clinvar_df['CLNSIG'].isin(['Pathogenic'])
    ]

    # Obliczenie kafli
    clinvar_counts = clinvar_df['CLNSIG'].value_counts()
    pathogenic_count = clinvar_counts.get("Pathogenic", 0)
    likely_pathogenic_count = clinvar_counts.get("Likely_pathogenic", 0)
    uncertain_count = clinvar_counts.get("Uncertain_significance", 0)

    clinvar_tiles = [
        StyledTile("Pathogenic", pathogenic_count),
        StyledTile("Likely Pathogenic", likely_pathogenic_count),
        StyledTile("Uncertain Significance", uncertain_count),
    ]
    elements.append(HorizontalTileRow(clinvar_tiles))
    elements.append(Spacer(1, 20))

    # Tabela ClinVar
    elements.append(Paragraph("Pathogenic Variants in ClinVar", section_title_style))
    elements.append(Spacer(1, 10))

    pathogenic_clinvar = clinvar_df[clinvar_df['CLNSIG'] == "Pathogenic"]
    if not pathogenic_clinvar.empty:
        # Przetworzenie genotypów na bardziej czytelną formę
        def interpret_genotype(genotype):
            genotype = str(genotype)
            if genotype == "[[0, 0, False]]":
                return "Homozygous Reference"
            elif genotype == "[[0, 1, False]]":
                return "Heterozygous"
            elif genotype == "[[1, 1, False]]":
                return "Homozygous Alternative"
            else:
                return "Unknown"

        pathogenic_clinvar["GENOTYPE_INTERPRET"] = pathogenic_clinvar["GENOTYPES"].apply(interpret_genotype)
        pathogenic_clinvar["DISEASE"] = pathogenic_clinvar["DISEASE"].apply(lambda x: truncate_text(x))

    if not pathogenic_clinvar.empty:
        clinvar_table_data = [["Chrom", "Position", "Ref", "Alt", "Gene", "Disease", "Genotype"]]
        clinvar_table_data += pathogenic_clinvar[["CHROM", "POS", "REF", "ALT", "GENEINFO", "DISEASE", "GENOTYPE_INTERPRET"]].values.tolist()

        column_widths = [30, 60, 20, 20, 115, 170, 110]
        clinvar_table = Table(clinvar_table_data, colWidths=column_widths)
        clinvar_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#356774")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#edf6f9")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), "DINCondensed"),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#edf6f9")),
            ('WORDWRAP', (0, 0), (-1, -1)),

        ]))
        elements.append(clinvar_table)
    else:
        elements.append(Paragraph("No pathogenic variants found in ClinVar.", text_style))

    elements.append(Spacer(1, 20))

    # Sekcja GWAS
    elements.append(Paragraph("GWAS Section", section_title_style))
    elements.append(Spacer(1, 10))

    # Filtracja wariantów GWAS
    filtered_gwas_df = gwas_df[
        gwas_df['Risk_Category'] == 'High Risk'
    ]

    # Obliczenie kafli
    gwas_counts = gwas_df['Risk_Category'].value_counts()
    high_risk_count = gwas_counts.get("High Risk", 0)
    medium_risk_count = gwas_counts.get("Normal Risk", 0)
    low_risk_count = gwas_counts.get("Low Risk", 0)

    gwas_tiles = [
        StyledTile("High Risk", high_risk_count),
        StyledTile("Normal Risk", medium_risk_count),
        StyledTile("Low Risk", low_risk_count),
    ]
    elements.append(HorizontalTileRow(gwas_tiles))
    elements.append(Spacer(1, 20))

    # Tabela GWAS
    elements.append(Paragraph("High Risk Variants in GWAS", section_title_style))
    elements.append(Spacer(1, 10))

    high_risk_gwas = gwas_df[gwas_df['Risk_Category'] == "High Risk"]
    if not high_risk_gwas.empty:
        gwas_table_data = [["Disease/Trait", "PRS", "Mean PRS", "Z-Score", "Risk Category"]]
        gwas_table_data += high_risk_gwas[["DISEASE/TRAIT", "PRS", "mean_prs", "z_score", "Risk_Category"]].values.tolist()
        gwas_table = Table(gwas_table_data)
        gwas_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#356774")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#edf6f9")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), "DINCondensed"),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#edf6f9"))
        ]))
        elements.append(gwas_table)
    else:
        elements.append(Paragraph("No high-risk variants found in GWAS.", text_style))

    elements.append(Spacer(1, 20))

    # Podsumowanie
    elements.append(Paragraph("Summary", section_title_style))
    summary_description = generate_summary_text(filtered_clinvar_df, filtered_gwas_df)
    summary_description = summary_description.replace("\n", "<br/>")
    elements.append(Paragraph(summary_description, text_style))

    # Generowanie dokumentu z tłem
    def on_first_page(canvas, doc):
        draw_background_on_page(canvas)

    def on_later_pages(canvas, doc):
        draw_background_on_page(canvas)

    doc.build(elements, onFirstPage=on_first_page, onLaterPages=on_later_pages)

    print(f"Raport wygenerowany: {output_file}")
