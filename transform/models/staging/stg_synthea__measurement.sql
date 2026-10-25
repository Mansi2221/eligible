-- Synthea numeric observations (labs + vitals) are LOINC-coded.
select
    'synthea'                                as source,
    patient_id                               as person_source_value,
    measurement_code                         as source_code,
    'LOINC'                                  as source_vocabulary,
    measurement_name,
    cast(value as double)                    as value_as_number,
    unit                                     as unit_source_value,
    cast(substr(measured_at, 1, 10) as date) as measurement_date
from {{ source('raw', 'synthea_measurements') }}
where measurement_code is not null
