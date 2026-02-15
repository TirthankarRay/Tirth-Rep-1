"""Tests for mock SCLC patient data generation."""
from app.seed_data import generate_patients, generate_json_seed_data


def test_generates_correct_number_of_patients():
    data = generate_patients(100)
    assert len(data["patients"]) == 100


def test_stage_distribution():
    data = generate_patients(1000)
    stages = [d["stage"] for d in data["diagnoses"]]
    ls_count = stages.count("LS-SCLC")
    es_count = stages.count("ES-SCLC")
    # 30% LS, 70% ES with some variance
    assert 200 < ls_count < 400
    assert 600 < es_count < 800


def test_all_patients_have_diagnosis():
    data = generate_patients(100)
    patient_ids = {p["patient_id"] for p in data["patients"]}
    diagnosed_ids = {d["patient_id"] for d in data["diagnoses"]}
    assert patient_ids == diagnosed_ids


def test_all_patients_have_first_line_treatment():
    data = generate_patients(100)
    patient_ids = {p["patient_id"] for p in data["patients"]}
    treated_ids = {
        t["patient_id"]
        for t in data["treatment_episodes"]
        if t["line_of_therapy"] == 1
    }
    assert patient_ids == treated_ids


def test_valid_stages():
    data = generate_patients(100)
    for d in data["diagnoses"]:
        assert d["stage"] in ("LS-SCLC", "ES-SCLC")


def test_valid_ecog_status():
    data = generate_patients(100)
    for d in data["diagnoses"]:
        assert 0 <= d["ecog_status"] <= 4


def test_json_serializable():
    data = generate_json_seed_data()
    for key in data:
        for record in data[key]:
            for v in record.values():
                assert not hasattr(v, "__dict__") or isinstance(v, (str, int, float, bool, type(None)))


def test_facilities_generated():
    data = generate_patients(100)
    assert len(data["facilities"]) > 0


def test_biomarker_tests_generated():
    data = generate_patients(100)
    assert len(data["biomarker_tests"]) > 0
