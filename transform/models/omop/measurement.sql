-- OMOP CDM measurement (Synthea LOINC labs + vitals).
with stg as (
    select * from {{ ref('stg_synthea__measurement') }}
)
select
    row_number() over (order by s.person_source_value) as measurement_id,
    p.person_id,
    s.source,
    s.source_code as measurement_source_value,
    s.source_vocabulary,
    s.measurement_name,
    s.value_as_number,
    s.unit_source_value,
    s.measurement_date
from stg s
join {{ ref('person') }} p
    on p.source = s.source
   and p.person_source_value = s.person_source_value
