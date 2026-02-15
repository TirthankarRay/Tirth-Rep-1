"""Generate realistic mock SCLC patient data.

Distributions based on clinical literature:
- Stage: 30% LS-SCLC, 70% ES-SCLC
- Age: median 70, range 45-85
- Gender: 50/50 M/F (historically male-predominant, now equalizing)
- Treatment: 40% chemo only, 50% chemo+IO, 10% clinical trial (ES-SCLC 1L)
"""
import random
import uuid
from datetime import date, timedelta

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

# Weighted state distribution (population-proportional approximation)
STATE_WEIGHTS = {
    "CA": 12, "TX": 9, "FL": 7, "NY": 6, "PA": 4, "IL": 4, "OH": 4,
    "GA": 3, "NC": 3, "MI": 3, "NJ": 3, "VA": 3, "WA": 2, "AZ": 2,
    "MA": 2, "TN": 2, "IN": 2, "MO": 2, "MD": 2, "WI": 2, "CO": 2,
    "MN": 2, "SC": 2, "AL": 2, "LA": 2, "KY": 2, "OR": 1, "OK": 1,
    "CT": 1, "IA": 1, "MS": 1, "AR": 1, "KS": 1, "NV": 1, "UT": 1,
    "NE": 1, "NM": 1, "WV": 1, "ID": 1, "HI": 1, "ME": 1, "NH": 1,
    "RI": 1, "MT": 1, "DE": 1, "SD": 1, "ND": 1, "AK": 1, "VT": 1,
    "WY": 1,
}

INSURANCE_TYPES = ["Medicare", "Commercial", "Medicaid", "Uninsured"]
INSURANCE_WEIGHTS = [55, 25, 15, 5]  # SCLC median age ~70, so heavy Medicare

RACE_ETHNICITY = ["White", "Black", "Hispanic", "Asian", "Other"]
RACE_WEIGHTS = [70, 15, 8, 4, 3]

SMOKING_STATUS = ["Current Smoker", "Former Smoker", "Never Smoker"]
SMOKING_WEIGHTS = [40, 55, 5]  # SCLC strongly associated with smoking

FACILITY_TYPES = ["Academic", "Community", "Veterans", "Rural"]
FACILITY_WEIGHTS = [30, 50, 10, 10]

REGIMEN_1L_ES = [
    ("Carboplatin/Etoposide + Atezolizumab", "Chemo+IO", True),
    ("Carboplatin/Etoposide + Durvalumab", "Chemo+IO", True),
    ("Carboplatin/Etoposide", "Chemo Only", False),
    ("Cisplatin/Etoposide", "Chemo Only", False),
    ("Clinical Trial", "Clinical Trial", False),
]
REGIMEN_1L_ES_WEIGHTS = [30, 20, 25, 15, 10]

REGIMEN_1L_LS = [
    ("Cisplatin/Etoposide + Concurrent RT", "Chemo+RT", False),
    ("Carboplatin/Etoposide + Concurrent RT", "Chemo+RT", False),
    ("Clinical Trial", "Clinical Trial", False),
]
REGIMEN_1L_LS_WEIGHTS = [50, 40, 10]

REGIMEN_2L = [
    ("Topotecan", "Chemo Only", False),
    ("Lurbinectedin", "Chemo Only", False),
    ("Platinum Re-challenge", "Chemo Only", False),
    ("Clinical Trial", "Clinical Trial", False),
    ("Nivolumab", "IO Only", True),
]
REGIMEN_2L_WEIGHTS = [30, 25, 15, 15, 15]

RESPONSE_TYPES = ["CR", "PR", "SD", "PD"]
PROGRESSION_SITES = ["Brain", "Liver", "Bone", "Adrenal", "Lung", "Lymph Nodes"]

BIOMARKER_TYPES = ["PD-L1", "TMB", "NGS"]


def weighted_choice(items, weights):
    return random.choices(items, weights=weights, k=1)[0]


def generate_age() -> date:
    """Generate DOB for median age ~70, range 45-85."""
    age = int(random.gauss(70, 8))
    age = max(45, min(85, age))
    base = date(2026, 1, 1)
    dob = base.replace(year=base.year - age) - timedelta(days=random.randint(0, 364))
    return dob


def generate_patients(n: int = 500) -> dict:
    """Generate n mock SCLC patients with full journey data."""
    random.seed(42)

    patients = []
    diagnoses = []
    biomarker_tests = []
    treatment_episodes = []
    response_assessments = []
    progression_events = []
    trial_enrollments = []
    facilities = []

    # Generate facilities first
    facility_ids = {}
    for st in US_STATES:
        for ft in FACILITY_TYPES:
            fid = uuid.uuid4()
            facility_ids[(st, ft)] = fid
            facilities.append({
                "facility_id": fid,
                "facility_name": f"{st} {ft} Medical Center",
                "facility_type": ft,
                "state": st,
                "city": f"{st} City",
            })

    states_list = list(STATE_WEIGHTS.keys())
    states_weights = list(STATE_WEIGHTS.values())

    for i in range(n):
        pid = uuid.uuid4()
        state = weighted_choice(states_list, states_weights)
        gender = random.choice(["Male", "Female"])
        dob = generate_age()
        insurance = weighted_choice(INSURANCE_TYPES, INSURANCE_WEIGHTS)
        race = weighted_choice(RACE_ETHNICITY, RACE_WEIGHTS)
        urban_rural = weighted_choice(["Urban", "Rural"], [75, 25])

        patients.append({
            "patient_id": pid,
            "external_id": f"SCLC-{i+1:05d}",
            "date_of_birth": dob,
            "gender": gender,
            "race_ethnicity": race,
            "state": state,
            "county": f"{state} County",
            "zip_code": f"{random.randint(10000, 99999)}",
            "insurance_type": insurance,
            "urban_rural": urban_rural,
        })

        # Diagnosis
        diag_date = date(2025, 1, 1) + timedelta(days=random.randint(0, 400))
        stage = weighted_choice(["LS-SCLC", "ES-SCLC"], [30, 70])
        ecog = weighted_choice([0, 1, 2, 3, 4], [10, 35, 30, 20, 5])
        smoking = weighted_choice(SMOKING_STATUS, SMOKING_WEIGHTS)
        facility_type = weighted_choice(FACILITY_TYPES, FACILITY_WEIGHTS)
        fac_id = facility_ids.get((state, facility_type))

        diagnoses.append({
            "diagnosis_id": uuid.uuid4(),
            "patient_id": pid,
            "diagnosis_date": diag_date,
            "stage": stage,
            "histology": "Small Cell Carcinoma",
            "ecog_status": ecog,
            "smoking_status": smoking,
            "diagnosing_facility_id": fac_id,
        })

        # Biomarker testing (~80% get PD-L1 tested)
        if random.random() < 0.80:
            test_date = diag_date + timedelta(days=random.randint(1, 7))
            result_date = test_date + timedelta(days=random.randint(3, 14))
            pdl1_pct = round(random.uniform(0, 100), 1)
            biomarker_tests.append({
                "test_id": uuid.uuid4(),
                "patient_id": pid,
                "test_date": test_date,
                "result_date": result_date,
                "biomarker_type": "PD-L1",
                "test_result": f"{pdl1_pct}%",
                "pdl1_percentage": pdl1_pct,
                "testing_facility_id": fac_id,
            })

        # TMB testing (~40%)
        if random.random() < 0.40:
            test_date = diag_date + timedelta(days=random.randint(1, 10))
            tmb = round(random.uniform(2, 30), 1)
            biomarker_tests.append({
                "test_id": uuid.uuid4(),
                "patient_id": pid,
                "test_date": test_date,
                "result_date": test_date + timedelta(days=random.randint(7, 21)),
                "biomarker_type": "TMB",
                "test_result": f"{tmb} mut/Mb",
                "tmb_score": tmb,
                "testing_facility_id": fac_id,
            })

        # First-line treatment
        ttt_days = max(1, int(random.gauss(18, 8)))  # median ~18 days
        tx_start = diag_date + timedelta(days=ttt_days)

        if stage == "ES-SCLC":
            regimen = weighted_choice(REGIMEN_1L_ES, REGIMEN_1L_ES_WEIGHTS)
        else:
            regimen = weighted_choice(REGIMEN_1L_LS, REGIMEN_1L_LS_WEIGHTS)

        tx_duration = random.randint(60, 150)
        episode_id_1l = uuid.uuid4()
        is_trial_1l = regimen[1] == "Clinical Trial"

        treatment_episodes.append({
            "episode_id": episode_id_1l,
            "patient_id": pid,
            "line_of_therapy": 1,
            "treatment_start_date": tx_start,
            "treatment_end_date": tx_start + timedelta(days=tx_duration),
            "regimen_name": regimen[0],
            "regimen_category": regimen[1],
            "includes_immunotherapy": regimen[2],
            "treating_facility_id": fac_id,
        })

        if is_trial_1l:
            trial_enrollments.append({
                "enrollment_id": uuid.uuid4(),
                "patient_id": pid,
                "trial_id": f"NCT{random.randint(10000000, 99999999)}",
                "trial_phase": weighted_choice(["Phase I", "Phase II", "Phase III"], [20, 40, 40]),
                "enrollment_date": tx_start - timedelta(days=random.randint(7, 21)),
                "trial_status": "Active",
            })

        # Response assessment (8-12 weeks after start)
        assess_date = tx_start + timedelta(days=random.randint(56, 84))
        if stage == "ES-SCLC":
            resp = weighted_choice(RESPONSE_TYPES, [5, 45, 20, 30])
        else:
            resp = weighted_choice(RESPONSE_TYPES, [15, 50, 15, 20])

        response_assessments.append({
            "assessment_id": uuid.uuid4(),
            "episode_id": episode_id_1l,
            "assessment_date": assess_date,
            "response_type": resp,
            "assessment_method": weighted_choice(["CT", "PET-CT", "Clinical"], [50, 35, 15]),
        })

        # Progression (~70% ES, ~50% LS progress)
        prog_chance = 0.70 if stage == "ES-SCLC" else 0.50
        if random.random() < prog_chance:
            pfs = random.randint(90, 250) if stage == "ES-SCLC" else random.randint(150, 400)
            prog_date = tx_start + timedelta(days=pfs)
            prog_site = random.choice(PROGRESSION_SITES)

            progression_events.append({
                "progression_id": uuid.uuid4(),
                "patient_id": pid,
                "progression_date": prog_date,
                "line_before_progression": 1,
                "pfs_days": pfs,
                "progression_site": prog_site,
            })

            # Second-line treatment (~80% of progressed patients)
            if random.random() < 0.80:
                tx2_start = prog_date + timedelta(days=random.randint(7, 28))
                regimen_2l = weighted_choice(REGIMEN_2L, REGIMEN_2L_WEIGHTS)
                episode_id_2l = uuid.uuid4()

                treatment_episodes.append({
                    "episode_id": episode_id_2l,
                    "patient_id": pid,
                    "line_of_therapy": 2,
                    "treatment_start_date": tx2_start,
                    "treatment_end_date": tx2_start + timedelta(days=random.randint(42, 120)),
                    "regimen_name": regimen_2l[0],
                    "regimen_category": regimen_2l[1],
                    "includes_immunotherapy": regimen_2l[2],
                    "treating_facility_id": fac_id,
                })

                # 2L response assessment
                assess2_date = tx2_start + timedelta(days=random.randint(42, 70))
                resp2 = weighted_choice(RESPONSE_TYPES, [2, 25, 25, 48])
                response_assessments.append({
                    "assessment_id": uuid.uuid4(),
                    "episode_id": episode_id_2l,
                    "assessment_date": assess2_date,
                    "response_type": resp2,
                    "assessment_method": "CT",
                })

                if regimen_2l[1] == "Clinical Trial":
                    trial_enrollments.append({
                        "enrollment_id": uuid.uuid4(),
                        "patient_id": pid,
                        "trial_id": f"NCT{random.randint(10000000, 99999999)}",
                        "trial_phase": weighted_choice(["Phase I", "Phase II", "Phase III"], [30, 40, 30]),
                        "enrollment_date": tx2_start - timedelta(days=random.randint(7, 14)),
                        "trial_status": "Active",
                    })

    return {
        "patients": patients,
        "diagnoses": diagnoses,
        "biomarker_tests": biomarker_tests,
        "treatment_episodes": treatment_episodes,
        "response_assessments": response_assessments,
        "progression_events": progression_events,
        "trial_enrollments": trial_enrollments,
        "facilities": facilities,
    }


def generate_json_seed_data() -> dict:
    """Generate seed data as JSON-serializable dicts for the frontend mock API."""
    data = generate_patients(500)
    # Convert UUIDs and dates to strings
    def serialize(records):
        result = []
        for r in records:
            row = {}
            for k, v in r.items():
                if isinstance(v, uuid.UUID):
                    row[k] = str(v)
                elif isinstance(v, date):
                    row[k] = v.isoformat()
                else:
                    row[k] = v
            result.append(row)
        return result

    return {k: serialize(v) for k, v in data.items()}


if __name__ == "__main__":
    import json
    data = generate_json_seed_data()
    print(json.dumps(data, indent=2)[:2000])
    print(f"\nGenerated:")
    for k, v in data.items():
        print(f"  {k}: {len(v)} records")
