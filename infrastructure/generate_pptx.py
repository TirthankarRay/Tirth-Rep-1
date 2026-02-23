"""
Generate Enterprise Architecture PowerPoint for SCLC Patient Journey Dashboard.
8 professional slides covering the full AWS + React JS architecture.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── Color Palette ──
NAVY       = RGBColor(0x1B, 0x2A, 0x4A)
DARK_NAVY  = RGBColor(0x0F, 0x1A, 0x33)
AWS_ORANGE = RGBColor(0xFF, 0x99, 0x00)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
MEDIUM_GRAY= RGBColor(0xBB, 0xBB, 0xBB)
DARK_GRAY  = RGBColor(0x44, 0x44, 0x44)
BLUE       = RGBColor(0x23, 0x6B, 0xB0)
GREEN      = RGBColor(0x2E, 0x7D, 0x32)
RED        = RGBColor(0xC6, 0x28, 0x28)
TEAL       = RGBColor(0x00, 0x96, 0x88)
PURPLE     = RGBColor(0x7B, 0x1F, 0xA2)
BRONZE_CLR = RGBColor(0xCD, 0x7F, 0x32)
SILVER_CLR = RGBColor(0xC0, 0xC0, 0xC0)
GOLD_CLR   = RGBColor(0xFF, 0xD7, 0x00)
LIGHT_BLUE = RGBColor(0xE3, 0xF2, 0xFD)
LIGHT_GREEN= RGBColor(0xE8, 0xF5, 0xE9)
LIGHT_ORANGE=RGBColor(0xFF, 0xF3, 0xE0)
LIGHT_PURPLE=RGBColor(0xF3, 0xE5, 0xF5)
LIGHT_TEAL = RGBColor(0xE0, 0xF2, 0xF1)
LIGHT_RED  = RGBColor(0xFF, 0xEB, 0xEE)

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def add_footer(slide):
    """Add consistent footer to every slide."""
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(7.0), Inches(8), Inches(0.4))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = "Confidential \u2014 SCLC Patient Journey Dashboard \u2014 Enterprise Architecture"
    p.font.size = Pt(8)
    p.font.color.rgb = MEDIUM_GRAY
    p.font.italic = True


def add_box(slide, left, top, width, height, text, fill_color, font_color=WHITE,
            font_size=10, bold=False, border_color=None, sub_text=None):
    """Add a rounded rectangle box with text."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.alignment = PP_ALIGN.CENTER
    tf.paragraphs[0].space_before = Pt(2)
    tf.paragraphs[0].space_after = Pt(0)
    if sub_text:
        p2 = tf.add_paragraph()
        p2.text = sub_text
        p2.font.size = Pt(font_size - 2)
        p2.font.color.rgb = font_color
        p2.alignment = PP_ALIGN.CENTER
    return shape


def add_arrow_down(slide, cx, top, length):
    """Add a downward arrow."""
    shape = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, cx - Inches(0.15), top, Inches(0.3), length)
    shape.fill.solid()
    shape.fill.fore_color.rgb = AWS_ORANGE
    shape.line.fill.background()
    return shape


def add_arrow_right(slide, left, cy, length):
    """Add a rightward arrow."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, left, cy - Inches(0.12), length, Inches(0.24))
    shape.fill.solid()
    shape.fill.fore_color.rgb = AWS_ORANGE
    shape.line.fill.background()
    return shape


def add_section_header(slide, left, top, width, text):
    """Add a section header bar."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Inches(0.35))
    shape.fill.solid()
    shape.fill.fore_color.rgb = NAVY
    shape.line.fill.background()
    tf = shape.text_frame
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(11)
    p.font.color.rgb = WHITE
    p.font.bold = True
    p.alignment = PP_ALIGN.LEFT
    return shape


# ═══════════════════════════════════════════════════════════════════
# SLIDE 1 — Title Slide
# ═══════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

# Background
bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
bg.fill.solid()
bg.fill.fore_color.rgb = DARK_NAVY
bg.line.fill.background()

# Accent bar
bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(3.0), SLIDE_W, Inches(0.06))
bar.fill.solid()
bar.fill.fore_color.rgb = AWS_ORANGE
bar.line.fill.background()

# Title
txBox = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(11), Inches(1.5))
tf = txBox.text_frame
p = tf.paragraphs[0]
p.text = "SCLC Patient Journey Analytics Dashboard"
p.font.size = Pt(36)
p.font.color.rgb = WHITE
p.font.bold = True
p.alignment = PP_ALIGN.CENTER

# Subtitle
txBox2 = slide.shapes.add_textbox(Inches(1), Inches(3.3), Inches(11), Inches(1.0))
tf2 = txBox2.text_frame
p2 = tf2.paragraphs[0]
p2.text = "Enterprise Architecture on AWS"
p2.font.size = Pt(24)
p2.font.color.rgb = AWS_ORANGE
p2.font.bold = True
p2.alignment = PP_ALIGN.CENTER

# Tech stack
txBox3 = slide.shapes.add_textbox(Inches(1), Inches(4.3), Inches(11), Inches(0.6))
tf3 = txBox3.text_frame
p3 = tf3.paragraphs[0]
p3.text = "AWS  \u00b7  React JS  \u00b7  Databricks  \u00b7  Redshift Serverless  \u00b7  Terraform"
p3.font.size = Pt(14)
p3.font.color.rgb = MEDIUM_GRAY
p3.alignment = PP_ALIGN.CENTER

# Date
txBox4 = slide.shapes.add_textbox(Inches(1), Inches(5.5), Inches(11), Inches(0.5))
tf4 = txBox4.text_frame
p4 = tf4.paragraphs[0]
p4.text = "February 2026  \u00b7  HIPAA Compliant  \u00b7  Production-Ready"
p4.font.size = Pt(12)
p4.font.color.rgb = MEDIUM_GRAY
p4.alignment = PP_ALIGN.CENTER

add_footer(slide)

# ═══════════════════════════════════════════════════════════════════
# SLIDE 2 — End-to-End Architecture Overview
# ═══════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])

# Title bar
title_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.7))
title_bar.fill.solid()
title_bar.fill.fore_color.rgb = NAVY
title_bar.line.fill.background()
tf = title_bar.text_frame
p = tf.paragraphs[0]
p.text = "  End-to-End Architecture Overview"
p.font.size = Pt(22)
p.font.color.rgb = WHITE
p.font.bold = True

# Layer boxes — vertical flow
layers = [
    ("DATA SOURCES", "EHR (HL7 FHIR)  \u00b7  Claims (EDI 837)  \u00b7  Labs  \u00b7  Cancer Registries", DARK_GRAY),
    ("S3 DATA LAKE", "Landing Zone  \u00b7  KMS Encrypted  \u00b7  Parquet/CSV  \u00b7  Lifecycle Policies", GREEN),
    ("DATABRICKS ON AWS", "Bronze \u2192 Silver \u2192 Gold  \u00b7  Delta Lake  \u00b7  Unity Catalog", BRONZE_CLR),
    ("AMAZON REDSHIFT SERVERLESS", "Serving Layer  \u00b7  Dim + Fact + Agg Tables  \u00b7  Materialized Views", BLUE),
    ("AWS LAMBDA + API GATEWAY", "7 REST Endpoints  \u00b7  Python 3.12  \u00b7  Cognito Auth  \u00b7  WAF", PURPLE),
    ("CLOUDFRONT + S3 (Frontend)", "React 18 + TypeScript  \u00b7  Recharts  \u00b7  Route 53  \u00b7  ACM TLS", AWS_ORANGE),
]

box_w = Inches(7.0)
box_h = Inches(0.7)
start_x = Inches(3.2)
start_y = Inches(1.0)
gap = Inches(0.25)

for i, (title, desc, color) in enumerate(layers):
    top = start_y + i * (box_h + gap + Inches(0.2))
    add_box(slide, start_x, top, box_w, box_h, title, color, WHITE, 12, True, sub_text=desc)
    if i < len(layers) - 1:
        add_arrow_down(slide, start_x + box_w / 2, top + box_h, Inches(0.2))

# Side annotations
annotations_left = [
    (Inches(1.0), "AWS Transfer Family\nSFTP / FTPS"),
    (Inches(2.0), "AWS Glue\nSchema Discovery"),
    (Inches(3.0), "Delta Live Tables\nPipeline Orchestration"),
    (Inches(4.0), "Redshift Data API\nServerless Queries"),
]

for y_offset, text in annotations_left:
    txBox = slide.shapes.add_textbox(Inches(0.3), start_y + y_offset, Inches(2.5), Inches(0.6))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(8)
    p.font.color.rgb = DARK_GRAY

# Right side — Security annotations
annotations_right = [
    (Inches(0.5), "KMS CMK\nEncryption"),
    (Inches(1.8), "VPC Private\nSubnets"),
    (Inches(3.1), "IAM Least\nPrivilege"),
    (Inches(4.4), "CloudTrail\nAudit Logs"),
]

for y_offset, text in annotations_right:
    txBox = slide.shapes.add_textbox(Inches(11.0), start_y + y_offset, Inches(2.0), Inches(0.6))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(8)
    p.font.color.rgb = DARK_GRAY

add_footer(slide)

# ═══════════════════════════════════════════════════════════════════
# SLIDE 3 — Data Pipeline (Medallion Architecture)
# ═══════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])

title_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.7))
title_bar.fill.solid()
title_bar.fill.fore_color.rgb = NAVY
title_bar.line.fill.background()
tf = title_bar.text_frame
p = tf.paragraphs[0]
p.text = "  Data Pipeline \u2014 Databricks Medallion Architecture"
p.font.size = Pt(22)
p.font.color.rgb = WHITE
p.font.bold = True

# Three tier boxes
tier_w = Inches(3.5)
tier_h = Inches(5.0)
tier_gap = Inches(0.8)
tier_start_x = Inches(0.7)
tier_start_y = Inches(1.2)

# Bronze
add_box(slide, tier_start_x, tier_start_y, tier_w, Inches(0.5),
        "BRONZE LAYER", BRONZE_CLR, WHITE, 14, True)
bronze_tables = [
    "bronze.ehr_patients", "bronze.ehr_encounters",
    "bronze.ehr_conditions", "bronze.ehr_procedures",
    "bronze.claims_professional", "bronze.claims_institutional",
    "bronze.claims_pharmacy"
]
for j, tbl in enumerate(bronze_tables):
    add_box(slide, tier_start_x + Inches(0.2), tier_start_y + Inches(0.7) + j * Inches(0.38),
            Inches(3.1), Inches(0.32), tbl, LIGHT_ORANGE, DARK_GRAY, 9)

# Arrow Bronze → Silver
add_arrow_right(slide, tier_start_x + tier_w, tier_start_y + Inches(2.0), tier_gap)

# Silver
silver_x = tier_start_x + tier_w + tier_gap
add_box(slide, silver_x, tier_start_y, tier_w, Inches(0.5),
        "SILVER LAYER", RGBColor(0x90, 0x90, 0x90), WHITE, 14, True)
silver_tables = [
    "silver.dim_patient", "silver.dim_facility",
    "silver.fact_diagnosis", "silver.fact_treatment_episode",
    "silver.fact_response_assessment", "silver.fact_biomarker_test",
    "silver.fact_progression_event", "silver.fact_trial_enrollment"
]
for j, tbl in enumerate(silver_tables):
    add_box(slide, silver_x + Inches(0.2), tier_start_y + Inches(0.7) + j * Inches(0.38),
            Inches(3.1), Inches(0.32), tbl, LIGHT_BLUE, DARK_GRAY, 9)

# Arrow Silver → Gold
gold_x = silver_x + tier_w + tier_gap
add_arrow_right(slide, silver_x + tier_w, tier_start_y + Inches(2.0), tier_gap)

# Gold
add_box(slide, gold_x, tier_start_y, tier_w, Inches(0.5),
        "GOLD LAYER", RGBColor(0xC8, 0xA2, 0x00), WHITE, 14, True)
gold_tables = [
    "gold.agg_overview_metrics", "gold.agg_time_to_treatment",
    "gold.agg_treatment_patterns", "gold.agg_geographic_metrics",
    "gold.agg_sankey_journey"
]
for j, tbl in enumerate(gold_tables):
    add_box(slide, gold_x + Inches(0.2), tier_start_y + Inches(0.7) + j * Inches(0.38),
            Inches(3.1), Inches(0.32), tbl, LIGHT_GREEN, DARK_GRAY, 9)

# Bottom bar — Pipeline info
add_box(slide, Inches(0.7), Inches(6.5), Inches(11.8), Inches(0.4),
        "Delta Lake  \u00b7  Unity Catalog Governance  \u00b7  Auto Loader (Incremental)  \u00b7  Schema Evolution  \u00b7  Daily Orchestration",
        NAVY, WHITE, 10, True)

add_footer(slide)

# ═══════════════════════════════════════════════════════════════════
# SLIDE 4 — Data Warehouse Schema (Star Schema)
# ═══════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])

title_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.7))
title_bar.fill.solid()
title_bar.fill.fore_color.rgb = NAVY
title_bar.line.fill.background()
tf = title_bar.text_frame
p = tf.paragraphs[0]
p.text = "  Amazon Redshift \u2014 Data Warehouse Schema"
p.font.size = Pt(22)
p.font.color.rgb = WHITE
p.font.bold = True

# Center — dim_patient (star center)
center_x, center_y = Inches(5.2), Inches(3.2)
dim_w, dim_h = Inches(2.8), Inches(1.6)
add_box(slide, center_x, center_y, dim_w, dim_h,
        "dim_patient", BLUE, WHITE, 14, True,
        sub_text="patient_id (DISTKEY)\ndate_of_birth, gender\nstate, insurance_type\nrace_ethnicity, urban_rural")

# dim_facility (top right)
add_box(slide, Inches(9.0), Inches(1.0), Inches(2.5), Inches(1.2),
        "dim_facility", BLUE, WHITE, 12, True,
        sub_text="facility_id, facility_name\nfacility_type, state, city\nDISTSTYLE ALL")

# dim_date (top left)
add_box(slide, Inches(1.5), Inches(1.0), Inches(2.5), Inches(1.2),
        "dim_date", BLUE, WHITE, 12, True,
        sub_text="date_key (YYYYMMDD)\nyear, quarter, month\nDISTSTYLE ALL")

# Fact tables arranged around dim_patient
facts = [
    ("fact_diagnosis", "diagnosis_date\nstage, histology\necog_status", Inches(0.5), Inches(3.0)),
    ("fact_treatment_episode", "treatment_start_date\nregimen_name, category\nline_of_therapy", Inches(0.5), Inches(5.0)),
    ("fact_biomarker_test", "test_date, biomarker_type\ntest_result, pdl1_%\ntmb_score", Inches(9.5), Inches(3.0)),
    ("fact_response_assessment", "assessment_date\nresponse_type (CR/PR/SD/PD)\nassessment_method", Inches(9.5), Inches(5.0)),
    ("fact_progression_event", "progression_date\npfs_days\nprogression_site", Inches(4.0), Inches(5.8)),
    ("fact_trial_enrollment", "enrollment_date\ntrial_phase\ntrial_status", Inches(7.5), Inches(5.8)),
]

for name, desc, x, y in facts:
    add_box(slide, x, y, Inches(3.0), Inches(1.3), name, GREEN, WHITE, 11, True, sub_text=desc)

# Aggregation tables (bottom)
add_section_header(slide, Inches(0.5), Inches(0.8), Inches(3.5), "  DIMENSION TABLES")
add_section_header(slide, Inches(4.5), Inches(0.8), Inches(4.0), "  FACT TABLES")
add_section_header(slide, Inches(9.0), Inches(0.8), Inches(4.0), "  Relationships: FK \u2192 dim_patient")

add_footer(slide)

# ═══════════════════════════════════════════════════════════════════
# SLIDE 5 — API & Compute Layer
# ═══════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])

title_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.7))
title_bar.fill.solid()
title_bar.fill.fore_color.rgb = NAVY
title_bar.line.fill.background()
tf = title_bar.text_frame
p = tf.paragraphs[0]
p.text = "  API & Compute Layer \u2014 AWS Lambda + API Gateway"
p.font.size = Pt(22)
p.font.color.rgb = WHITE
p.font.bold = True

# Left — Client
add_box(slide, Inches(0.5), Inches(2.5), Inches(1.5), Inches(2.0),
        "React\nDashboard", TEAL, WHITE, 12, True, sub_text="Browser\nClient")

# Arrow to Cognito
add_arrow_right(slide, Inches(2.0), Inches(3.5), Inches(0.8))

# Cognito
add_box(slide, Inches(2.8), Inches(2.0), Inches(2.0), Inches(1.0),
        "Amazon Cognito", PURPLE, WHITE, 11, True, sub_text="JWT Auth + MFA")

# Arrow to API GW
add_arrow_right(slide, Inches(2.8) + Inches(2.0), Inches(3.5), Inches(0.5))

# API Gateway
add_box(slide, Inches(5.3), Inches(1.5), Inches(2.5), Inches(4.5),
        "API Gateway", AWS_ORANGE, WHITE, 14, True)

# Lambda functions (right side)
lambdas = [
    ("fn_metrics_overview", "GET /metrics/overview"),
    ("fn_metrics_ttt", "GET /metrics/time-to-treatment"),
    ("fn_metrics_treatment_patterns", "GET /metrics/treatment-patterns"),
    ("fn_geographic_states", "GET /geographic/states"),
    ("fn_patients_list", "GET /patients"),
    ("fn_patients_detail", "GET /patients/{id}"),
    ("fn_journey_sankey", "GET /patients/journey/sankey"),
]

lambda_x = Inches(8.5)
for i, (name, route) in enumerate(lambdas):
    y = Inches(1.2) + i * Inches(0.75)
    add_box(slide, lambda_x, y, Inches(3.8), Inches(0.65),
            f"\u03bb {name}", PURPLE, WHITE, 9, True, sub_text=route)
    # Arrow from API GW to Lambda
    add_arrow_right(slide, Inches(7.8), y + Inches(0.3), Inches(0.6))

# Bottom — Redshift
add_box(slide, Inches(9.0), Inches(6.3), Inches(3.5), Inches(0.6),
        "Amazon Redshift Serverless (via Data API)", BLUE, WHITE, 10, True)

# Cache note
add_box(slide, Inches(5.3), Inches(6.3), Inches(3.0), Inches(0.6),
        "API Gateway Cache: 300s metrics, 60s patients", LIGHT_BLUE, DARK_GRAY, 9)

add_footer(slide)

# ═══════════════════════════════════════════════════════════════════
# SLIDE 6 — Frontend Hosting & CDN
# ═══════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])

title_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.7))
title_bar.fill.solid()
title_bar.fill.fore_color.rgb = NAVY
title_bar.line.fill.background()
tf = title_bar.text_frame
p = tf.paragraphs[0]
p.text = "  Frontend Hosting & CDN"
p.font.size = Pt(22)
p.font.color.rgb = WHITE
p.font.bold = True

# Flow: User → Route53 → CloudFront → WAF → S3
hosting_items = [
    ("End User\nBrowser", DARK_GRAY, Inches(0.3)),
    ("Route 53\nDNS", BLUE, Inches(2.5)),
    ("CloudFront\nCDN (Edge)", AWS_ORANGE, Inches(4.7)),
    ("WAF v2\nProtection", RED, Inches(6.9)),
    ("S3 Bucket\n(OAC)", GREEN, Inches(9.1)),
]

for name, color, x in hosting_items:
    add_box(slide, x, Inches(1.5), Inches(1.8), Inches(1.2), name, color, WHITE, 12, True)

for i in range(len(hosting_items) - 1):
    x = hosting_items[i][2] + Inches(1.8)
    add_arrow_right(slide, x, Inches(2.1), Inches(0.6))

# ACM
add_box(slide, Inches(11.3), Inches(1.5), Inches(1.5), Inches(1.2),
        "ACM\nTLS 1.3", TEAL, WHITE, 11, True)

# React component tree
add_section_header(slide, Inches(0.5), Inches(3.3), Inches(12.3), "  React Application Component Tree")

components = [
    ("App.tsx", NAVY, Inches(5.5), Inches(3.8)),
    ("Dashboard.tsx", BLUE, Inches(5.0), Inches(4.6)),
    ("FilterPanel", TEAL, Inches(0.5), Inches(5.5)),
    ("KPICardRow", GREEN, Inches(2.5), Inches(5.5)),
    ("TimeToTreatmentChart", PURPLE, Inches(4.5), Inches(5.5)),
    ("TreatmentPatternsChart", AWS_ORANGE, Inches(7.0), Inches(5.5)),
    ("GeographicHeatMap", RED, Inches(9.3), Inches(5.5)),
    ("PatientTable", BLUE, Inches(11.2), Inches(5.5)),
]

for name, color, x, y in components:
    add_box(slide, x, y, Inches(1.8), Inches(0.5), name, color, WHITE, 8, True)

# Data layer
add_box(slide, Inches(0.5), Inches(6.3), Inches(4.0), Inches(0.5),
        "Zustand Store  \u00b7  React Query  \u00b7  API Service", LIGHT_BLUE, DARK_GRAY, 9, True)
add_box(slide, Inches(5.0), Inches(6.3), Inches(4.0), Inches(0.5),
        "TypeScript Types  \u00b7  Recharts  \u00b7  Tailwind CSS", LIGHT_GREEN, DARK_GRAY, 9, True)

add_footer(slide)

# ═══════════════════════════════════════════════════════════════════
# SLIDE 7 — Security & Compliance (HIPAA)
# ═══════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])

title_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.7))
title_bar.fill.solid()
title_bar.fill.fore_color.rgb = NAVY
title_bar.line.fill.background()
tf = title_bar.text_frame
p = tf.paragraphs[0]
p.text = "  Security & Compliance \u2014 HIPAA Architecture"
p.font.size = Pt(22)
p.font.color.rgb = WHITE
p.font.bold = True

# VPC boundary
vpc_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(1.0), Inches(12.3), Inches(5.0))
vpc_shape.fill.solid()
vpc_shape.fill.fore_color.rgb = LIGHT_BLUE
vpc_shape.line.color.rgb = BLUE
vpc_shape.line.width = Pt(2)
tf = vpc_shape.text_frame
p = tf.paragraphs[0]
p.text = "VPC (10.0.0.0/16) \u2014 2 Availability Zones"
p.font.size = Pt(12)
p.font.color.rgb = BLUE
p.font.bold = True

# Public subnets
add_box(slide, Inches(1.0), Inches(1.6), Inches(5.0), Inches(1.2),
        "PUBLIC SUBNETS", GREEN, WHITE, 11, True,
        sub_text="NAT Gateway  \u00b7  Internet Gateway\n10.0.1.0/24  \u00b7  10.0.2.0/24")

# Private subnets
add_box(slide, Inches(6.5), Inches(1.6), Inches(5.5), Inches(1.2),
        "PRIVATE SUBNETS", PURPLE, WHITE, 11, True,
        sub_text="Lambda Functions (VPC-attached)\n10.0.11.0/24  \u00b7  10.0.12.0/24")

# Data subnets
add_box(slide, Inches(1.0), Inches(3.2), Inches(5.0), Inches(1.2),
        "DATA SUBNETS (Isolated)", RED, WHITE, 11, True,
        sub_text="Redshift Serverless  \u00b7  No Internet\n10.0.21.0/24  \u00b7  10.0.22.0/24")

# VPC Endpoints
add_box(slide, Inches(6.5), Inches(3.2), Inches(5.5), Inches(1.2),
        "VPC ENDPOINTS (PrivateLink)", TEAL, WHITE, 11, True,
        sub_text="Secrets Manager  \u00b7  Redshift Data API\nCloudWatch Logs  \u00b7  S3 Gateway")

# Encryption section
add_box(slide, Inches(1.0), Inches(4.8), Inches(3.5), Inches(1.0),
        "Encryption", NAVY, WHITE, 11, True,
        sub_text="KMS CMK (at rest)\nTLS 1.2+ (in transit)\nS3 SSE  \u00b7  Redshift SSE")

# IAM
add_box(slide, Inches(5.0), Inches(4.8), Inches(3.5), Inches(1.0),
        "Identity & Access", NAVY, WHITE, 11, True,
        sub_text="IAM Least Privilege\nCognito (JWT + MFA)\nSAML/OIDC Federation")

# Audit
add_box(slide, Inches(9.0), Inches(4.8), Inches(3.5), Inches(1.0),
        "Audit & Monitoring", NAVY, WHITE, 11, True,
        sub_text="CloudTrail (API logs)\nAWS Config (compliance)\nGuardDuty (threats)\nVPC Flow Logs")

# BAA note
add_box(slide, Inches(0.5), Inches(6.2), Inches(12.3), Inches(0.4),
        "AWS Business Associate Agreement (BAA) in place  \u00b7  PHI encrypted at rest and in transit  \u00b7  All access logged and auditable",
        DARK_NAVY, WHITE, 9, True)

add_footer(slide)

# ═══════════════════════════════════════════════════════════════════
# SLIDE 8 — CI/CD & Monitoring
# ═══════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])

title_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.7))
title_bar.fill.solid()
title_bar.fill.fore_color.rgb = NAVY
title_bar.line.fill.background()
tf = title_bar.text_frame
p = tf.paragraphs[0]
p.text = "  CI/CD Pipelines & Monitoring"
p.font.size = Pt(22)
p.font.color.rgb = WHITE
p.font.bold = True

# CI/CD Section
add_section_header(slide, Inches(0.5), Inches(1.0), Inches(6.0), "  GitHub Actions CI/CD Pipelines")

pipelines = [
    ("deploy-frontend.yml", "Build React \u2192 S3 \u2192 CloudFront Invalidation", GREEN),
    ("deploy-lambda.yml", "Test \u2192 Package \u2192 Deploy Lambda Functions", PURPLE),
    ("deploy-infra.yml", "Terraform Validate \u2192 Plan \u2192 Apply", BLUE),
    ("quality-gate.yml", "Lint \u2192 Type Check \u2192 Test \u2192 Security Scan", AWS_ORANGE),
]

for i, (name, desc, color) in enumerate(pipelines):
    y = Inches(1.5) + i * Inches(0.8)
    add_box(slide, Inches(0.5), y, Inches(6.0), Inches(0.65), name, color, WHITE, 11, True, sub_text=desc)

# Environment promotion
add_section_header(slide, Inches(0.5), Inches(4.8), Inches(6.0), "  Environment Promotion")

envs = [("DEV", GREEN, Inches(0.5)), ("STAGING", AWS_ORANGE, Inches(2.5)), ("PROD", RED, Inches(4.5))]
for name, color, x in envs:
    add_box(slide, x, Inches(5.3), Inches(1.8), Inches(0.6), name, color, WHITE, 12, True)

add_arrow_right(slide, Inches(2.3), Inches(5.6), Inches(0.2))
add_arrow_right(slide, Inches(4.3), Inches(5.6), Inches(0.2))

add_box(slide, Inches(0.5), Inches(6.1), Inches(6.0), Inches(0.5),
        "Auto-deploy to Dev  \u00b7  Manual approval for Staging/Prod  \u00b7  OIDC Auth (no static keys)",
        LIGHT_BLUE, DARK_GRAY, 9)

# Monitoring Section
add_section_header(slide, Inches(7.0), Inches(1.0), Inches(5.8), "  CloudWatch Monitoring & Observability")

monitoring_items = [
    ("CloudWatch Dashboards", "API latency, error rates\nLambda duration, invocations\nRedshift query performance", BLUE),
    ("CloudWatch Alarms", "5xx rate > 1%\nLambda errors > 5 / 5min\nLambda p99 > 10s\nRedshift queue > 10", RED),
    ("AWS X-Ray", "Distributed tracing\nLambda \u2192 Redshift calls\nLatency analysis", TEAL),
    ("SNS Alerts", "Email notifications\nto ops team\non alarm trigger", AWS_ORANGE),
]

for i, (name, desc, color) in enumerate(monitoring_items):
    y = Inches(1.5) + i * Inches(1.2)
    add_box(slide, Inches(7.0), y, Inches(5.8), Inches(1.0), name, color, WHITE, 11, True, sub_text=desc)

add_footer(slide)

# ═══════════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════════
output_path = "/home/user/Tirth-Rep-1/infrastructure/SCLC_Architecture_Diagrams.pptx"
prs.save(output_path)
print(f"PowerPoint saved to: {output_path}")
print(f"Total slides: {len(prs.slides)}")
