-- Synthea patients -> normalized person shape.
select
    'synthea'                                     as source,
    patient_id                                    as person_source_value,
    case lower(gender)
        when 'male' then 'MALE'
        when 'female' then 'FEMALE'
    end                                           as gender,
    cast(substr(birth_date, 1, 4) as integer)     as year_of_birth,
    race,
    ethnicity
from {{ source('raw', 'synthea_patients') }}
