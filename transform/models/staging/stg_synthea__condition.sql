-- Synthea conditions are already SNOMED-coded, so source == standard code.
select
    'synthea'                          as source,
    patient_id                         as person_source_value,
    condition_code                     as source_code,
    'SNOMED'                           as source_vocabulary,
    condition_code                     as standard_code,
    condition_name,
    cast(substr(onset_date, 1, 10) as date) as condition_start_date
from {{ source('raw', 'synthea_conditions') }}
where condition_code is not null
