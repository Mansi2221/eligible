-- Legacy diagnoses are ICD-10; resolve to a standard SNOMED code via the
-- crosswalk seed. Diagnosis text is cleaned and falls back to the standard name.
with raw as (
    select * from read_csv_auto('{{ var("legacy_csv") }}', header = true, all_varchar = true)
)
select
    'legacy'                                             as source,
    raw.MRN                                              as person_source_value,
    raw.ICD10_CODE                                       as source_code,
    'ICD10'                                              as source_vocabulary,
    x.snomed_code                                        as standard_code,
    coalesce(nullif(trim(raw.DIAGNOSIS_TEXT), ''), x.standard_name) as condition_name,
    try_strptime(raw.DIAG_DATE, ['%m/%d/%Y', '%m-%d-%Y'])::date     as condition_start_date
from raw
left join {{ ref('icd10_to_standard') }} x
    on x.icd10_code = raw.ICD10_CODE
