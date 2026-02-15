import type {
  OverviewMetrics,
  TimeToTreatmentResponse,
  TreatmentPatternsResponse,
  GeographicResponse,
  PatientDetail,
  SankeyResponse,
} from '../types/index';

// ---------------------------------------------------------------------------
// Seeded pseudo-random number generator (Mulberry32)
// Keeps data deterministic across reloads.
// ---------------------------------------------------------------------------
function createRng(seed: number) {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rng = createRng(20240101);

/** Return a random integer between min and max inclusive. */
function randInt(min: number, max: number): number {
  return Math.floor(rng() * (max - min + 1)) + min;
}

/** Pick a random element from an array. */
function pick<T>(arr: T[]): T {
  return arr[Math.floor(rng() * arr.length)];
}

/** Generate a normally-distributed value (Box-Muller) clamped to [lo, hi]. */
function randNormal(mean: number, stddev: number, lo: number, hi: number): number {
  let u = 0;
  let v = 0;
  while (u === 0) u = rng();
  while (v === 0) v = rng();
  let value = mean + stddev * Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
  value = Math.round(value);
  if (value < lo) value = lo;
  if (value > hi) value = hi;
  return value;
}

/** Format a Date as YYYY-MM-DD. */
function fmt(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** Return a date that is `days` days after `base`. */
function addDays(base: Date, days: number): Date {
  const d = new Date(base);
  d.setDate(d.getDate() + days);
  return d;
}

// ---------------------------------------------------------------------------
// 1. Overview Metrics
// ---------------------------------------------------------------------------
export const mockOverviewMetrics: OverviewMetrics = {
  total_patients: 500,
  new_diagnoses_mtd: 42,
  new_diagnoses_qtd: 128,
  new_diagnoses_ytd: 387,
  median_time_to_treatment_days: 17.5,
  biomarker_testing_rate: 78.4,
  immunotherapy_uptake_rate: 62.3,
  clinical_trial_enrollment_rate: 12.8,
};

// ---------------------------------------------------------------------------
// 2. Time to Treatment
// ---------------------------------------------------------------------------
export const mockTimeToTreatment: TimeToTreatmentResponse = {
  distribution: [
    { bucket: '0-7',   count: 65,  percentage: 13.0 },
    { bucket: '8-14',  count: 115, percentage: 23.0 },
    { bucket: '15-21', count: 155, percentage: 31.0 },
    { bucket: '22-30', count: 105, percentage: 21.0 },
    { bucket: '31+',   count: 60,  percentage: 12.0 },
  ],
  median_days: 17.5,
  mean_days: 19.3,
  target_days: 21,
  within_target_rate: 67.0,
};

// ---------------------------------------------------------------------------
// 3. Treatment Patterns
// ---------------------------------------------------------------------------
export const mockTreatmentPatterns: TreatmentPatternsResponse = {
  first_line: [
    { regimen_category: 'Platinum + Etoposide',              count: 160, percentage: 32.0 },
    { regimen_category: 'Platinum + Etoposide + Atezolizumab', count: 145, percentage: 29.0 },
    { regimen_category: 'Platinum + Etoposide + Durvalumab',   count: 105, percentage: 21.0 },
    { regimen_category: 'Clinical Trial Regimen',              count: 50,  percentage: 10.0 },
    { regimen_category: 'Concurrent Chemoradiation',           count: 30,  percentage: 6.0  },
    { regimen_category: 'Other',                               count: 10,  percentage: 2.0  },
  ],
  second_line: [
    { regimen_category: 'Topotecan',          count: 95,  percentage: 35.2 },
    { regimen_category: 'Lurbinectedin',      count: 65,  percentage: 24.1 },
    { regimen_category: 'CAV',                count: 35,  percentage: 13.0 },
    { regimen_category: 'Clinical Trial',     count: 30,  percentage: 11.1 },
    { regimen_category: 'Re-challenge Platin', count: 25,  percentage: 9.3  },
    { regimen_category: 'Other',              count: 20,  percentage: 7.4  },
  ],
  total_episodes: 770,
};

// ---------------------------------------------------------------------------
// 4. Geographic Data – all 50 states + DC
// Weights loosely proportional to US population. Patient counts sum to 500.
// ---------------------------------------------------------------------------
const statePopWeights: Record<string, number> = {
  AL: 15, AK: 2, AZ: 22, AR: 9, CA: 60, CO: 17, CT: 11, DE: 3, DC: 2, FL: 40,
  GA: 25, HI: 4, ID: 6, IL: 30, IN: 16, IA: 10, KS: 9, KY: 13, LA: 14, ME: 4,
  MD: 18, MA: 20, MI: 24, MN: 17, MS: 9, MO: 18, MT: 3, NE: 6, NV: 10, NH: 4,
  NJ: 22, NM: 6, NY: 38, NC: 25, ND: 2, OH: 28, OK: 12, OR: 13, PA: 30, RI: 3,
  SC: 15, SD: 3, TN: 20, TX: 55, UT: 10, VT: 2, VA: 25, WA: 23, WV: 5, WI: 17,
  WY: 2,
};

function buildGeographicData(): GeographicResponse {
  const totalWeight = Object.values(statePopWeights).reduce((a, b) => a + b, 0);
  let allocated = 0;
  const entries = Object.entries(statePopWeights);
  const states = entries.map(([abbr, w], idx) => {
    let count: number;
    if (idx === entries.length - 1) {
      count = 500 - allocated;
    } else {
      count = Math.round((w / totalWeight) * 500);
    }
    allocated += count;
    return {
      state: abbr,
      patient_count: count,
      median_time_to_treatment: parseFloat((14 + rng() * 12).toFixed(1)),
      biomarker_testing_rate: parseFloat((65 + rng() * 25).toFixed(1)),
      immunotherapy_uptake_rate: parseFloat((48 + rng() * 30).toFixed(1)),
    };
  });
  return { states };
}

export const mockGeographicData: GeographicResponse = buildGeographicData();

// ---------------------------------------------------------------------------
// 5. Patient Details (50 records)
// ---------------------------------------------------------------------------
const GENDERS = ['Male', 'Female'];
const RACE_OPTIONS = [
  'White', 'White', 'White', 'White',           // ~55 %
  'Black or African American', 'Black or African American', // ~15 %
  'Hispanic or Latino', 'Hispanic or Latino',    // ~15 %
  'Asian',                                       // ~7 %
  'Other',                                       // ~8 %
];
const INSURANCE_TYPES = ['Medicare', 'Medicare', 'Medicare', 'Commercial', 'Medicaid', 'VA', 'Uninsured'];
const URBAN_RURAL = ['Urban', 'Urban', 'Urban', 'Suburban', 'Rural'];
const SMOKING_STATUS = ['Current', 'Current', 'Former', 'Former', 'Former', 'Never'];
const HISTOLOGIES = [
  'Small cell carcinoma', 'Small cell carcinoma', 'Small cell carcinoma',
  'Combined small cell carcinoma',
];
const BIOMARKER_TYPES = ['PD-L1', 'TMB', 'Ki-67', 'TTF-1', 'Synaptophysin'];

const STATE_ABBRS = Object.keys(statePopWeights);

function generatePatient(index: number): PatientDetail {
  const id = `P-${String(index + 1).padStart(5, '0')}`;
  const birthYear = 2025 - randNormal(70, 8, 45, 85);
  const birthMonth = randInt(1, 12);
  const birthDay = randInt(1, 28);
  const dob = new Date(birthYear, birthMonth - 1, birthDay);

  const gender = pick(GENDERS);
  const stage = rng() < 0.30 ? 'LS-SCLC' : 'ES-SCLC';

  // Diagnosis date: sometime between 2023-01 and 2025-12
  const diagBase = new Date(2023, 0, 1);
  const diagDate = addDays(diagBase, randInt(0, 1094));

  const diagnosis = {
    diagnosis_id: `DX-${String(index + 1).padStart(5, '0')}`,
    patient_id: id,
    diagnosis_date: fmt(diagDate),
    stage,
    histology: pick(HISTOLOGIES),
    ecog_status: pick([0, 1, 1, 1, 2, 2, 3]),
    smoking_status: pick(SMOKING_STATUS),
  };

  // First-line treatment: starts 7-35 days after diagnosis
  const tttDays = randNormal(18, 7, 3, 60);
  const tx1Start = addDays(diagDate, tttDays);
  const tx1End = addDays(tx1Start, randInt(63, 126)); // 9-18 weeks

  // Determine regimen category
  const r = rng();
  let regimenCategory: string;
  let regimenName: string;
  let includesIO: boolean;
  if (r < 0.40) {
    regimenCategory = 'Chemotherapy Only';
    regimenName = pick(['Carboplatin + Etoposide', 'Cisplatin + Etoposide']);
    includesIO = false;
  } else if (r < 0.90) {
    regimenCategory = 'Chemo + Immunotherapy';
    regimenName = pick([
      'Carboplatin + Etoposide + Atezolizumab',
      'Carboplatin + Etoposide + Durvalumab',
      'Cisplatin + Etoposide + Atezolizumab',
    ]);
    includesIO = true;
  } else {
    regimenCategory = 'Clinical Trial';
    regimenName = pick([
      'Trial: DLL3-targeting BiTE + Chemo',
      'Trial: Anti-TIGIT + Chemo + IO',
      'Trial: Tarlatamab monotherapy',
    ]);
    includesIO = rng() < 0.5;
  }

  const episode1: PatientDetail['treatment_episodes'][0] = {
    episode_id: `EP-${String(index + 1).padStart(5, '0')}-1`,
    patient_id: id,
    line_of_therapy: 1,
    treatment_start_date: fmt(tx1Start),
    treatment_end_date: fmt(tx1End),
    regimen_name: regimenName,
    regimen_category: regimenCategory,
    includes_immunotherapy: includesIO,
  };

  const episodes = [episode1];

  // ~54% of patients receive second-line therapy
  if (rng() < 0.54) {
    const tx2Start = addDays(tx1End, randInt(14, 90));
    const tx2End = addDays(tx2Start, randInt(42, 105));
    const secondLineName = pick([
      'Topotecan', 'Lurbinectedin', 'CAV (Cyclophosphamide/Doxorubicin/Vincristine)',
      'Irinotecan', 'Temozolomide', 'Carboplatin + Etoposide re-challenge',
    ]);
    episodes.push({
      episode_id: `EP-${String(index + 1).padStart(5, '0')}-2`,
      patient_id: id,
      line_of_therapy: 2,
      treatment_start_date: fmt(tx2Start),
      treatment_end_date: fmt(tx2End),
      regimen_name: secondLineName,
      regimen_category: secondLineName.includes('re-challenge') ? 'Re-challenge Platinum' : secondLineName.split(' ')[0],
      includes_immunotherapy: false,
    });
  }

  // Biomarker tests
  const biomarkerTests: PatientDetail['biomarker_tests'] = [];
  const numTests = pick([1, 1, 2, 2, 2, 3]);
  for (let t = 0; t < numTests; t++) {
    const testDate = addDays(diagDate, randInt(-7, 14));
    const resultDate = addDays(testDate, randInt(3, 10));
    const bType = BIOMARKER_TYPES[t % BIOMARKER_TYPES.length];
    let testResult: string | null = null;
    let pdl1: number | null = null;
    let tmb: number | null = null;
    if (bType === 'PD-L1') {
      pdl1 = pick([0, 0, 1, 1, 2, 5, 10, 15, 25, 50]);
      testResult = pdl1 >= 1 ? 'Positive' : 'Negative';
    } else if (bType === 'TMB') {
      tmb = parseFloat((rng() * 25 + 2).toFixed(1));
      testResult = tmb >= 10 ? 'High' : 'Low';
    } else {
      testResult = pick(['Positive', 'Positive', 'Positive', 'Negative']);
    }
    biomarkerTests.push({
      test_id: `BM-${String(index + 1).padStart(5, '0')}-${t + 1}`,
      patient_id: id,
      test_date: fmt(testDate),
      result_date: fmt(resultDate),
      biomarker_type: bType,
      test_result: testResult,
      pdl1_percentage: pdl1,
      tmb_score: tmb,
    });
  }

  return {
    patient_id: id,
    external_id: `EXT-${randInt(100000, 999999)}`,
    date_of_birth: fmt(dob),
    gender,
    race_ethnicity: pick(RACE_OPTIONS),
    state: pick(STATE_ABBRS),
    county: pick([
      'Jefferson', 'Cook', 'Harris', 'Maricopa', 'San Diego',
      'Orange', 'Kings', 'Clark', 'Tarrant', 'Bexar',
      'Wayne', 'Middlesex', 'Alameda', 'Franklin', 'Suffolk',
    ]),
    insurance_type: pick(INSURANCE_TYPES),
    urban_rural: pick(URBAN_RURAL),
    created_at: '2024-01-15T08:00:00Z',
    updated_at: '2025-06-01T12:00:00Z',
    diagnoses: [diagnosis],
    treatment_episodes: episodes,
    biomarker_tests: biomarkerTests,
  };
}

export const mockPatients: PatientDetail[] = Array.from({ length: 50 }, (_, i) => generatePatient(i));

// ---------------------------------------------------------------------------
// 6. Sankey Data – Patient journey flow
// ---------------------------------------------------------------------------
export const mockSankeyData: SankeyResponse = {
  nodes: [
    // Diagnosis stage
    { id: 'dx_ls',       label: 'LS-SCLC Diagnosis',      count: 150 },
    { id: 'dx_es',       label: 'ES-SCLC Diagnosis',      count: 350 },
    // Biomarker testing
    { id: 'bio_tested',  label: 'Biomarker Tested',        count: 392 },
    { id: 'bio_not',     label: 'Not Tested',              count: 108 },
    // First-line treatment
    { id: 'tx1_chemo',   label: '1L Chemo Only',           count: 200 },
    { id: 'tx1_chemio',  label: '1L Chemo + IO',           count: 250 },
    { id: 'tx1_trial',   label: '1L Clinical Trial',       count: 50  },
    // First-line outcome
    { id: 'resp_cr_pr',  label: 'Response (CR/PR)',        count: 330 },
    { id: 'resp_sd',     label: 'Stable Disease',          count: 85  },
    { id: 'resp_pd',     label: 'Progressive Disease',     count: 85  },
    // Second-line
    { id: 'tx2_topo',    label: '2L Topotecan',            count: 95  },
    { id: 'tx2_lurbi',   label: '2L Lurbinectedin',        count: 65  },
    { id: 'tx2_other',   label: '2L Other',                count: 110 },
    { id: 'no_tx2',      label: 'No 2L Treatment',         count: 230 },
  ],
  links: [
    // Diagnosis -> Biomarker testing
    { source: 'dx_ls',       target: 'bio_tested',  value: 128 },
    { source: 'dx_ls',       target: 'bio_not',     value: 22  },
    { source: 'dx_es',       target: 'bio_tested',  value: 264 },
    { source: 'dx_es',       target: 'bio_not',     value: 86  },

    // Biomarker -> First-line treatment
    { source: 'bio_tested',  target: 'tx1_chemo',   value: 130 },
    { source: 'bio_tested',  target: 'tx1_chemio',  value: 220 },
    { source: 'bio_tested',  target: 'tx1_trial',   value: 42  },
    { source: 'bio_not',     target: 'tx1_chemo',   value: 70  },
    { source: 'bio_not',     target: 'tx1_chemio',  value: 30  },
    { source: 'bio_not',     target: 'tx1_trial',   value: 8   },

    // First-line -> Response
    { source: 'tx1_chemo',   target: 'resp_cr_pr',  value: 120 },
    { source: 'tx1_chemo',   target: 'resp_sd',     value: 40  },
    { source: 'tx1_chemo',   target: 'resp_pd',     value: 40  },
    { source: 'tx1_chemio',  target: 'resp_cr_pr',  value: 175 },
    { source: 'tx1_chemio',  target: 'resp_sd',     value: 40  },
    { source: 'tx1_chemio',  target: 'resp_pd',     value: 35  },
    { source: 'tx1_trial',   target: 'resp_cr_pr',  value: 35  },
    { source: 'tx1_trial',   target: 'resp_sd',     value: 5   },
    { source: 'tx1_trial',   target: 'resp_pd',     value: 10  },

    // Response -> Second-line
    { source: 'resp_cr_pr',  target: 'tx2_topo',    value: 50  },
    { source: 'resp_cr_pr',  target: 'tx2_lurbi',   value: 40  },
    { source: 'resp_cr_pr',  target: 'tx2_other',   value: 55  },
    { source: 'resp_cr_pr',  target: 'no_tx2',      value: 185 },
    { source: 'resp_sd',     target: 'tx2_topo',    value: 25  },
    { source: 'resp_sd',     target: 'tx2_lurbi',   value: 15  },
    { source: 'resp_sd',     target: 'tx2_other',   value: 30  },
    { source: 'resp_sd',     target: 'no_tx2',      value: 15  },
    { source: 'resp_pd',     target: 'tx2_topo',    value: 20  },
    { source: 'resp_pd',     target: 'tx2_lurbi',   value: 10  },
    { source: 'resp_pd',     target: 'tx2_other',   value: 25  },
    { source: 'resp_pd',     target: 'no_tx2',      value: 30  },
  ],
};
