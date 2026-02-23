# SCLC Patient Journey Analytics Dashboard — Enterprise Architecture

## Overview

This document describes the enterprise-grade AWS architecture for the SCLC (Small Cell Lung Cancer) Patient Journey Analytics Dashboard. The platform ingests clinical data from multiple healthcare sources, processes it through a medallion data pipeline, and serves interactive analytics via a React JS dashboard.

**Tech Stack:** AWS + React JS + Databricks + Terraform

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        END-TO-END ARCHITECTURE                             │
│                                                                             │
│   DATA SOURCES ──► S3 DATA LAKE ──► DATABRICKS ──► REDSHIFT ──► LAMBDA    │
│   (EHR, Claims)    (Landing Zone)   (Bronze/Silver   (Serving)    (API)    │
│                                      /Gold)                        │       │
│                                                                    ▼       │
│                                                         CLOUDFRONT + S3    │
│                                                         (React Dashboard)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Data Ingestion Layer

### Source Systems
| Source | Format | Protocol | Frequency |
|--------|--------|----------|-----------|
| EHR Systems | HL7 FHIR (JSON) | AWS Transfer Family (SFTP) | Real-time / Daily |
| Claims Data | EDI 837 (CSV) | S3 Direct Upload | Daily batch |
| Lab Systems | HL7 v2 / CSV | AWS Transfer Family | Real-time |
| Cancer Registries | CSV / Parquet | S3 Direct Upload | Weekly |

### S3 Landing Zone
```
s3://sclc-data-lake-{env}/
├── raw/
│   ├── ehr/{YYYY}/{MM}/{DD}/          # EHR FHIR bundles
│   ├── claims/{YYYY}/{MM}/{DD}/       # Claims files
│   ├── labs/{YYYY}/{MM}/{DD}/         # Lab results
│   └── registries/{YYYY}/{MM}/{DD}/   # Registry exports
├── processed/                          # Databricks intermediate
├── curated/                            # Gold-tier outputs
├── staging/redshift/                   # Redshift COPY staging
└── checkpoints/                        # Auto Loader checkpoints
```

### AWS Services
- **AWS Transfer Family** — Managed SFTP/FTPS endpoints for EHR and lab data
- **AWS Glue Crawlers** — Schema discovery and Data Catalog registration
- **S3 Encryption** — AWS KMS Customer Managed Key (CMK) for all data at rest
- **S3 Lifecycle** — Raw → Infrequent Access (90 days) → Glacier (365 days)

---

## 2. Data Processing Layer — Databricks on AWS

### Medallion Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   BRONZE     │     │   SILVER     │     │    GOLD      │
│              │     │              │     │              │
│ Raw Ingest   │────►│ Clean/Dedupe │────►│ Pre-Agg KPIs │
│ Schema-on-   │     │ Conform Dims │     │ Dashboard-   │
│ Read         │     │ + Facts      │     │ Ready Tables │
│              │     │              │     │              │
│ Delta Lake   │     │ Delta Lake   │     │ Delta Lake   │
│ Auto Loader  │     │ SCD Type 2   │     │ Overwrite    │
└──────────────┘     └──────────────┘     └──────────────┘
```

### Bronze Tables
| Table | Source | Description |
|-------|--------|-------------|
| `bronze.ehr_patients` | EHR | Raw patient demographics |
| `bronze.ehr_encounters` | EHR | Clinical encounters |
| `bronze.ehr_conditions` | EHR | Diagnoses / conditions |
| `bronze.ehr_procedures` | EHR | Procedures performed |
| `bronze.ehr_observations` | EHR | Lab observations |
| `bronze.claims_professional` | Claims | Professional claims |
| `bronze.claims_institutional` | Claims | Institutional claims |
| `bronze.claims_pharmacy` | Claims | Pharmacy claims |

### Silver Tables (Dimension + Fact)
| Table | Distribution | Sort Key | Description |
|-------|-------------|----------|-------------|
| `silver.dim_patient` | patient_id | state, created_at | Master patient dimension (SCD2) |
| `silver.dim_facility` | ALL | — | Facility reference data |
| `silver.fact_diagnosis` | patient_id | diagnosis_date | SCLC diagnoses (LS/ES staging) |
| `silver.fact_treatment_episode` | patient_id | treatment_start_date | Treatment regimens by line |
| `silver.fact_response_assessment` | patient_id | assessment_date | RECIST response (CR/PR/SD/PD) |
| `silver.fact_biomarker_test` | patient_id | test_date | PD-L1, TMB, NGS results |
| `silver.fact_progression_event` | patient_id | progression_date | Disease progression events |
| `silver.fact_trial_enrollment` | patient_id | enrollment_date | Clinical trial participation |

### Gold Tables (Pre-Aggregated)
| Table | Maps To | Description |
|-------|---------|-------------|
| `gold.agg_overview_metrics` | `GET /metrics/overview` | KPI summary metrics |
| `gold.agg_time_to_treatment` | `GET /metrics/time-to-treatment` | TTT distribution buckets |
| `gold.agg_treatment_patterns` | `GET /metrics/treatment-patterns` | Regimen usage by line |
| `gold.agg_geographic_metrics` | `GET /geographic/states` | State-level metrics |
| `gold.agg_sankey_journey` | `GET /patients/journey/sankey` | Patient flow transitions |

### Pipeline Notebooks
| # | Notebook | Layer | Schedule |
|---|----------|-------|----------|
| 01 | `bronze/01_ingest_ehr.py` | Bronze | Continuous (Auto Loader) |
| 02 | `bronze/02_ingest_claims.py` | Bronze | Daily 2:00 AM |
| 03 | `silver/03_patients.py` | Silver | Daily 3:00 AM |
| 04 | `silver/04_clinical.py` | Silver | Daily 3:30 AM |
| 05 | `gold/05_overview_metrics.py` | Gold | Daily 4:00 AM |
| 06 | `gold/06_treatment_analytics.py` | Gold | Daily 4:15 AM |
| 07 | `gold/07_geographic.py` | Gold | Daily 4:30 AM |
| 08 | `gold/08_sankey_journey.py` | Gold | Daily 4:45 AM |
| 09 | `gold/09_export_to_redshift.py` | Export | Daily 5:00 AM |

### Governance
- **Unity Catalog** — Centralized metadata, lineage, and access control
- **Delta Lake** — ACID transactions, schema evolution, time travel (30-day retention)
- **Data Quality** — Expectations and constraints at each layer boundary

---

## 3. Data Warehouse Layer — Amazon Redshift Serverless

### Configuration
| Property | Dev | Prod |
|----------|-----|------|
| Workgroup | `sclc-dev` | `sclc-prod` |
| Base RPU | 32 | 128 |
| Enhanced VPC Routing | Yes | Yes |
| Encryption | KMS CMK | KMS CMK |
| Publicly Accessible | No | No |

### Schemas
| Schema | Purpose | Access |
|--------|---------|--------|
| `sclc_core` | Dimension and fact tables | ETL write, Analyst read |
| `sclc_analytics` | Pre-aggregated tables | ETL write, Dashboard read |
| `sclc_staging` | ETL staging area | ETL only |

### Materialized Views
- `mv_patient_latest_status` — Latest stage, treatment, and facility per patient
- `mv_treatment_timeline` — Flat join of patient + diagnosis + treatment + response
- `mv_kpi_current` — Most recent snapshot from `agg_overview_metrics`

### Roles
| Role | Permissions |
|------|-------------|
| `sclc_readonly` | SELECT on `sclc_analytics` + materialized views |
| `sclc_analyst` | SELECT on `sclc_core` + `sclc_analytics` |
| `sclc_etl` | ALL on `sclc_staging`, INSERT/UPDATE/DELETE on core + analytics |
| `sclc_admin` | ALL on all schemas |

---

## 4. API Layer — AWS Lambda + API Gateway

### Endpoints
| Function | Method | Path | Cache TTL |
|----------|--------|------|-----------|
| `fn_metrics_overview` | GET | `/api/v1/metrics/overview` | 300s |
| `fn_metrics_ttt` | GET | `/api/v1/metrics/time-to-treatment` | 300s |
| `fn_metrics_treatment_patterns` | GET | `/api/v1/metrics/treatment-patterns` | 300s |
| `fn_geographic_states` | GET | `/api/v1/geographic/states` | 300s |
| `fn_patients_list` | GET | `/api/v1/patients` | 60s |
| `fn_patients_detail` | GET | `/api/v1/patients/{id}` | 60s |
| `fn_journey_sankey` | GET | `/api/v1/patients/journey/sankey` | 300s |

### Lambda Configuration
- **Runtime:** Python 3.12
- **Memory:** 256 MB
- **Timeout:** 15 seconds
- **VPC:** Private subnets with security group `sg_lambda`
- **Data Access:** Redshift Data API (boto3, no JDBC driver needed)
- **Shared Layer:** `db.py` (Redshift helper), `auth.py` (JWT validation)

### API Gateway
- **Type:** REST API (Regional endpoint)
- **Authorization:** Cognito User Pool authorizer (JWT)
- **Caching:** Enabled per endpoint (see table above)
- **Throttling:** 1000 requests/second, 2000 burst
- **Access Logging:** CloudWatch Logs

---

## 5. Frontend Hosting — S3 + CloudFront

### Architecture
```
End User ──► Route 53 ──► CloudFront ──► WAF v2 ──► S3 Bucket
(Browser)     (DNS)        (CDN Edge)   (Firewall)   (React Build)
```

### React Application Stack
- **React 18** with TypeScript 5.3
- **Recharts** — Data visualization (bar, pie, geographic)
- **TanStack React Query** — Server state management
- **Zustand** — Client state (filters)
- **Tailwind CSS** — Styling
- **Vite** — Build tooling

### CloudFront Configuration
| Property | Value |
|----------|-------|
| Origin | S3 with OAC (Origin Access Control) |
| Protocol | HTTPS only (redirect HTTP) |
| TLS Version | TLS 1.3 |
| Price Class | PriceClass_100 (US/EU) |
| Error Pages | 403→/index.html, 404→/index.html (SPA) |
| Cache Policy | CachingOptimized |
| Certificate | ACM (us-east-1) |

### WAF v2 Rules
- Rate limiting: 1000 requests per 5 minutes per IP
- AWS Managed Rules: CommonRuleSet, SQLiRuleSet, KnownBadInputsRuleSet
- Geographic restriction: US only (configurable)

---

## 6. Authentication & Authorization

### Amazon Cognito
| Property | Value |
|----------|-------|
| User Pool | `sclc-dashboard-{env}` |
| MFA | Optional (TOTP), Required for Admin |
| Password Policy | Min 12 chars, uppercase, lowercase, number, symbol |
| Token Validity | Access: 1 hour, Refresh: 30 days |
| Federation | SAML/OIDC for enterprise SSO |

### User Groups
| Group | Dashboard Access |
|-------|-----------------|
| Admin | Full access + user management |
| Analyst | All data views + export |
| Viewer | Read-only dashboard (default) |

### Auth Flow
```
Browser → Cognito Login → JWT Token → API Gateway (Cognito Authorizer) → Lambda
```

---

## 7. Security & Compliance (HIPAA)

### Network Architecture
```
┌─────────────────────────────────── VPC (10.0.0.0/16) ─────────────────────┐
│                                                                            │
│  ┌─ Public Subnets ──────────┐  ┌─ Private Subnets ─────────────────────┐ │
│  │ 10.0.1.0/24 (AZ-a)       │  │ 10.0.11.0/24 (AZ-a)                  │ │
│  │ 10.0.2.0/24 (AZ-b)       │  │ 10.0.12.0/24 (AZ-b)                  │ │
│  │                           │  │                                        │ │
│  │ • Internet Gateway        │  │ • Lambda Functions (VPC-attached)      │ │
│  │ • NAT Gateway             │  │ • VPC Endpoints                        │ │
│  └───────────────────────────┘  └────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Data Subnets (Isolated) ─────────────────────────────────────────────┐ │
│  │ 10.0.21.0/24 (AZ-a)                                                  │ │
│  │ 10.0.22.0/24 (AZ-b)                                                  │ │
│  │                                                                        │ │
│  │ • Redshift Serverless (no internet access)                            │ │
│  │ • Enhanced VPC Routing                                                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

### Encryption
| Layer | Method |
|-------|--------|
| S3 (at rest) | AWS KMS CMK (SSE-KMS) |
| Redshift (at rest) | AWS KMS CMK |
| CloudWatch Logs (at rest) | AWS KMS CMK |
| Secrets Manager | AWS KMS CMK |
| In transit | TLS 1.2+ everywhere |

### Compliance Controls
- **CloudTrail** — All API calls logged, 90-day retention
- **AWS Config** — Continuous compliance monitoring
- **GuardDuty** — Threat detection and anomaly monitoring
- **VPC Flow Logs** — Network traffic analysis
- **BAA** — AWS Business Associate Agreement in place
- **IAM** — Least-privilege roles per service, no shared credentials
- **Secrets Manager** — All credentials rotated automatically

---

## 8. Monitoring & Observability

### CloudWatch Dashboards
- **API Performance** — Request count, latency (p50/p90/p99), 4xx/5xx rates
- **Lambda Health** — Invocations, duration, errors, throttles per function
- **Redshift Performance** — Query duration, connections, queue depth

### Alarms
| Alarm | Threshold | Action |
|-------|-----------|--------|
| API 5xx Rate | > 1% over 5 min | SNS → Email |
| Lambda Errors | > 5 in 5 min (per fn) | SNS → Email |
| Lambda Duration p99 | > 10 seconds | SNS → Email |
| Redshift Queue Depth | > 10 queries | SNS → Email |

### Tracing
- **AWS X-Ray** — Distributed tracing across Lambda → Redshift Data API
- **Structured Logging** — JSON format, correlation IDs per request

---

## 9. CI/CD & Infrastructure as Code

### Terraform Modules
| Module | Resources |
|--------|-----------|
| `modules/vpc` | VPC, subnets, NAT GW, IGW, security groups, VPC endpoints |
| `modules/s3` | Data lake bucket, frontend bucket, policies |
| `modules/redshift` | Serverless namespace/workgroup, IAM role, secrets |
| `modules/lambda` | 7 functions, API Gateway, Lambda layer, IAM |
| `modules/cloudfront` | Distribution, OAC, WAF, Route 53 |
| `modules/security` | KMS, Cognito, CloudTrail, AWS Config |
| `modules/monitoring` | CloudWatch dashboards, alarms, SNS |

### GitHub Actions Pipelines
| Workflow | Trigger | Steps |
|----------|---------|-------|
| `deploy-frontend.yml` | Push to main (frontend/) | Build → S3 Sync → CloudFront Invalidate |
| `deploy-lambda.yml` | Push to main (lambda/) | Test → Package → Deploy Functions |
| `deploy-infra.yml` | Push to main (terraform/) | Validate → Plan → Apply |
| `quality-gate.yml` | Pull Request | Lint → Type Check → Test → Security Scan |

### Environment Promotion
```
DEV (auto-deploy) ──► STAGING (manual approval) ──► PROD (2 reviewers)
```

### State Management
- **Terraform State** — S3 backend with DynamoDB locking
- **Secrets** — AWS Secrets Manager (never in code or CI/CD variables)
- **Auth** — OIDC federation for GitHub Actions (no static AWS keys)

---

## 10. Cost Estimation (Monthly)

| Service | Dev | Prod |
|---------|-----|------|
| Redshift Serverless | $150 | $800 |
| Lambda (7 functions) | $5 | $50 |
| API Gateway | $5 | $30 |
| S3 (Data Lake + Frontend) | $20 | $100 |
| CloudFront | $10 | $50 |
| Databricks (Compute) | $200 | $1,500 |
| Cognito | $0 | $50 |
| CloudWatch / X-Ray | $15 | $75 |
| KMS | $5 | $10 |
| NAT Gateway | $35 | $70 |
| **Total** | **~$445/mo** | **~$2,735/mo** |

---

## 11. Disaster Recovery

| Component | Strategy | RPO | RTO |
|-----------|----------|-----|-----|
| S3 Data Lake | Cross-region replication | 15 min | 1 hour |
| Redshift | Automated snapshots (every 8 hours) | 8 hours | 30 min |
| Lambda Functions | Code in Git (re-deploy) | 0 | 15 min |
| Frontend | Code in Git (re-deploy to S3) | 0 | 10 min |
| Cognito | Export user pool backup | 24 hours | 2 hours |
| Terraform State | S3 versioned + cross-region replication | 15 min | 30 min |

### Recovery Procedure
1. Switch Route 53 to DR region (if multi-region)
2. Restore Redshift from latest snapshot
3. Re-deploy Lambda + API Gateway via Terraform
4. Re-deploy frontend to DR CloudFront
5. Verify all endpoints return expected data
