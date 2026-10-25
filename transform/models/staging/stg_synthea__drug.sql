-- Synthea medications are RxNorm-coded (source == standard).
select
    'synthea'                              as source,
    patient_id                             as person_source_value,
    drug_code                              as source_code,
    'RxNorm'                               as source_vocabulary,
    drug_name,
    cast(substr(authored_on, 1, 10) as date) as drug_exposure_start_date
from {{ source('raw', 'synthea_medications') }}
where drug_code is not null
