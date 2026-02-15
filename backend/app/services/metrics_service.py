from datetime import date, datetime

from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.diagnosis import Diagnosis
from app.models.treatment_episode import TreatmentEpisode
from app.models.biomarker_test import BiomarkerTest
from app.models.trial_enrollment import TrialEnrollment
from app.schemas.metrics import (
    OverviewMetrics,
    TimeToTreatmentBucket,
    TimeToTreatmentResponse,
    TreatmentPatternItem,
    TreatmentPatternsResponse,
    StateMetric,
    GeographicResponse,
    SankeyNode,
    SankeyLink,
    SankeyResponse,
)


async def get_overview_metrics(
    db: AsyncSession,
    stage: str | None = None,
    state: str | None = None,
) -> OverviewMetrics:
    today = date.today()
    month_start = today.replace(day=1)
    quarter_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start = today.replace(month=quarter_month, day=1)
    year_start = today.replace(month=1, day=1)

    base_filter = []
    if stage:
        base_filter.append(Diagnosis.stage == stage)
    if state:
        base_filter.append(Patient.state == state)

    # Total patients
    q = select(func.count(func.distinct(Patient.patient_id))).select_from(Patient)
    if state:
        q = q.where(Patient.state == state)
    result = await db.execute(q)
    total_patients = result.scalar() or 0

    # New diagnoses
    async def count_diagnoses_since(since: date) -> int:
        q = (
            select(func.count())
            .select_from(Diagnosis)
            .join(Patient, Diagnosis.patient_id == Patient.patient_id)
            .where(Diagnosis.diagnosis_date >= since)
        )
        for f in base_filter:
            q = q.where(f)
        r = await db.execute(q)
        return r.scalar() or 0

    mtd = await count_diagnoses_since(month_start)
    qtd = await count_diagnoses_since(quarter_start)
    ytd = await count_diagnoses_since(year_start)

    # Median time to treatment
    ttt_q = (
        select(
            func.extract("epoch", func.cast(TreatmentEpisode.treatment_start_date, type_=None))
            - func.extract("epoch", func.cast(Diagnosis.diagnosis_date, type_=None))
        )
        .select_from(Diagnosis)
        .join(TreatmentEpisode, and_(
            Diagnosis.patient_id == TreatmentEpisode.patient_id,
            TreatmentEpisode.line_of_therapy == 1,
        ))
        .join(Patient, Diagnosis.patient_id == Patient.patient_id)
    )
    for f in base_filter:
        ttt_q = ttt_q.where(f)
    result = await db.execute(ttt_q)
    ttt_values = [row[0] / 86400.0 for row in result.fetchall() if row[0] is not None and row[0] >= 0]
    median_ttt = sorted(ttt_values)[len(ttt_values) // 2] if ttt_values else None

    # Biomarker testing rate
    patients_with_diag = (
        select(func.count(func.distinct(Diagnosis.patient_id)))
        .select_from(Diagnosis)
        .join(Patient, Diagnosis.patient_id == Patient.patient_id)
    )
    for f in base_filter:
        patients_with_diag = patients_with_diag.where(f)
    r = await db.execute(patients_with_diag)
    total_diagnosed = r.scalar() or 0

    patients_with_biomarker = (
        select(func.count(func.distinct(BiomarkerTest.patient_id)))
        .select_from(BiomarkerTest)
        .join(Patient, BiomarkerTest.patient_id == Patient.patient_id)
    )
    if state:
        patients_with_biomarker = patients_with_biomarker.where(Patient.state == state)
    r = await db.execute(patients_with_biomarker)
    tested = r.scalar() or 0
    biomarker_rate = (tested / total_diagnosed * 100) if total_diagnosed > 0 else 0

    # Immunotherapy uptake (ES-SCLC first-line)
    es_first_line = (
        select(func.count())
        .select_from(TreatmentEpisode)
        .join(Patient, TreatmentEpisode.patient_id == Patient.patient_id)
        .join(Diagnosis, TreatmentEpisode.patient_id == Diagnosis.patient_id)
        .where(TreatmentEpisode.line_of_therapy == 1)
        .where(Diagnosis.stage == "ES-SCLC")
    )
    if state:
        es_first_line = es_first_line.where(Patient.state == state)
    r = await db.execute(es_first_line)
    total_es_1l = r.scalar() or 0

    es_io = (
        select(func.count())
        .select_from(TreatmentEpisode)
        .join(Patient, TreatmentEpisode.patient_id == Patient.patient_id)
        .join(Diagnosis, TreatmentEpisode.patient_id == Diagnosis.patient_id)
        .where(TreatmentEpisode.line_of_therapy == 1)
        .where(Diagnosis.stage == "ES-SCLC")
        .where(TreatmentEpisode.includes_immunotherapy.is_(True))
    )
    if state:
        es_io = es_io.where(Patient.state == state)
    r = await db.execute(es_io)
    io_count = r.scalar() or 0
    io_rate = (io_count / total_es_1l * 100) if total_es_1l > 0 else 0

    # Clinical trial enrollment rate
    patients_in_trials = (
        select(func.count(func.distinct(TrialEnrollment.patient_id)))
        .select_from(TrialEnrollment)
        .join(Patient, TrialEnrollment.patient_id == Patient.patient_id)
    )
    if state:
        patients_in_trials = patients_in_trials.where(Patient.state == state)
    r = await db.execute(patients_in_trials)
    trial_count = r.scalar() or 0
    trial_rate = (trial_count / total_patients * 100) if total_patients > 0 else 0

    return OverviewMetrics(
        total_patients=total_patients,
        new_diagnoses_mtd=mtd,
        new_diagnoses_qtd=qtd,
        new_diagnoses_ytd=ytd,
        median_time_to_treatment_days=round(median_ttt, 1) if median_ttt is not None else None,
        biomarker_testing_rate=round(biomarker_rate, 1),
        immunotherapy_uptake_rate=round(io_rate, 1),
        clinical_trial_enrollment_rate=round(trial_rate, 1),
    )


async def get_time_to_treatment(
    db: AsyncSession,
    stage: str | None = None,
    state: str | None = None,
) -> TimeToTreatmentResponse:
    q = (
        select(
            (func.cast(TreatmentEpisode.treatment_start_date, type_=None)
             - func.cast(Diagnosis.diagnosis_date, type_=None))
        )
        .select_from(Diagnosis)
        .join(TreatmentEpisode, and_(
            Diagnosis.patient_id == TreatmentEpisode.patient_id,
            TreatmentEpisode.line_of_therapy == 1,
        ))
        .join(Patient, Diagnosis.patient_id == Patient.patient_id)
    )
    if stage:
        q = q.where(Diagnosis.stage == stage)
    if state:
        q = q.where(Patient.state == state)

    result = await db.execute(q)
    days_list = [row[0].days if hasattr(row[0], "days") else int(row[0]) for row in result.fetchall() if row[0] is not None]

    if not days_list:
        return TimeToTreatmentResponse(
            distribution=[],
            median_days=None,
            mean_days=None,
            target_days=21,
            within_target_rate=0,
        )

    buckets = {"0-7": 0, "8-14": 0, "15-21": 0, "22-30": 0, "31+": 0}
    for d in days_list:
        if d <= 7:
            buckets["0-7"] += 1
        elif d <= 14:
            buckets["8-14"] += 1
        elif d <= 21:
            buckets["15-21"] += 1
        elif d <= 30:
            buckets["22-30"] += 1
        else:
            buckets["31+"] += 1

    total = len(days_list)
    distribution = [
        TimeToTreatmentBucket(bucket=k, count=v, percentage=round(v / total * 100, 1))
        for k, v in buckets.items()
    ]

    sorted_days = sorted(days_list)
    median = sorted_days[len(sorted_days) // 2]
    mean = sum(days_list) / total
    within_target = sum(1 for d in days_list if d <= 21) / total * 100

    return TimeToTreatmentResponse(
        distribution=distribution,
        median_days=median,
        mean_days=round(mean, 1),
        target_days=21,
        within_target_rate=round(within_target, 1),
    )


async def get_treatment_patterns(
    db: AsyncSession,
    stage: str | None = None,
) -> TreatmentPatternsResponse:
    async def get_patterns_for_line(line: int) -> list[TreatmentPatternItem]:
        q = (
            select(
                TreatmentEpisode.regimen_category,
                func.count().label("cnt"),
            )
            .select_from(TreatmentEpisode)
            .where(TreatmentEpisode.line_of_therapy == line)
        )
        if stage:
            q = (
                q.join(Diagnosis, TreatmentEpisode.patient_id == Diagnosis.patient_id)
                .where(Diagnosis.stage == stage)
            )
        q = q.group_by(TreatmentEpisode.regimen_category)
        result = await db.execute(q)
        rows = result.fetchall()
        total = sum(r.cnt for r in rows) or 1
        return [
            TreatmentPatternItem(
                regimen_category=r.regimen_category or "Unknown",
                count=r.cnt,
                percentage=round(r.cnt / total * 100, 1),
            )
            for r in rows
        ]

    first = await get_patterns_for_line(1)
    second = await get_patterns_for_line(2)
    total_episodes_q = select(func.count()).select_from(TreatmentEpisode)
    r = await db.execute(total_episodes_q)
    total = r.scalar() or 0

    return TreatmentPatternsResponse(first_line=first, second_line=second, total_episodes=total)


async def get_geographic_data(
    db: AsyncSession,
    metric_type: str = "patient_count",
) -> GeographicResponse:
    q = (
        select(Patient.state, func.count().label("patient_count"))
        .select_from(Patient)
        .where(Patient.state.isnot(None))
        .group_by(Patient.state)
    )
    result = await db.execute(q)
    states = [
        StateMetric(state=row.state, patient_count=row.patient_count)
        for row in result.fetchall()
    ]
    return GeographicResponse(states=states)


async def get_sankey_data(
    db: AsyncSession,
    stage: str | None = None,
) -> SankeyResponse:
    # Build Sankey: Diagnosis → Stage → 1L Treatment → Response → 2L Treatment
    base = select(Diagnosis.patient_id, Diagnosis.stage).select_from(Diagnosis)
    if stage:
        base = base.where(Diagnosis.stage == stage)
    result = await db.execute(base)
    diag_rows = result.fetchall()

    stage_counts: dict[str, int] = {}
    patient_stages: dict = {}
    for row in diag_rows:
        s = row.stage or "Unknown"
        stage_counts[s] = stage_counts.get(s, 0) + 1
        patient_stages[row.patient_id] = s

    # 1L treatment categories
    q = (
        select(TreatmentEpisode.patient_id, TreatmentEpisode.regimen_category)
        .where(TreatmentEpisode.line_of_therapy == 1)
    )
    result = await db.execute(q)
    treatment_rows = result.fetchall()
    patient_1l: dict = {}
    for row in treatment_rows:
        patient_1l[row.patient_id] = row.regimen_category or "Unknown"

    # Response assessments for 1L
    q = (
        select(TreatmentEpisode.patient_id, ResponseAssessment.response_type)
        .select_from(ResponseAssessment)
        .join(TreatmentEpisode, ResponseAssessment.episode_id == TreatmentEpisode.episode_id)
        .where(TreatmentEpisode.line_of_therapy == 1)
    )
    from app.models.response_assessment import ResponseAssessment
    result = await db.execute(q)
    resp_rows = result.fetchall()
    patient_response: dict = {}
    for row in resp_rows:
        patient_response[row.patient_id] = row.response_type or "Unknown"

    nodes: dict[str, int] = {}
    links: dict[tuple[str, str], int] = {}

    def add_node(nid: str):
        nodes[nid] = nodes.get(nid, 0) + 1

    def add_link(src: str, tgt: str):
        links[(src, tgt)] = links.get((src, tgt), 0) + 1

    for pid, stg in patient_stages.items():
        add_node(f"stage_{stg}")
        add_link("diagnosis", f"stage_{stg}")

        if pid in patient_1l:
            cat = patient_1l[pid]
            add_node(f"1l_{cat}")
            add_link(f"stage_{stg}", f"1l_{cat}")

            if pid in patient_response:
                resp = patient_response[pid]
                add_node(f"resp_{resp}")
                add_link(f"1l_{cat}", f"resp_{resp}")

    add_node("diagnosis")

    node_list = [SankeyNode(id=k, label=k.split("_", 1)[-1] if "_" in k else k, count=v) for k, v in nodes.items()]
    link_list = [SankeyLink(source=s, target=t, value=v) for (s, t), v in links.items()]

    return SankeyResponse(nodes=node_list, links=link_list)
