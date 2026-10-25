-- OMOP CDM condition_occurrence. Unifies SNOMED (synthea) and ICD-10->SNOMED
-- (legacy) conditions under one standard code, linked to the surrogate person_id.
with unioned as (
    select * from {{ ref('stg_synthea__condition') }}
    union all
    select * from {{ ref('stg_legacy__condition') }}
)
select
    row_number() over (order by u.source, u.person_source_value) as condition_occurrence_id,
    p.person_id,
    u.source,
    u.source_code            as condition_source_value,
    u.source_vocabulary,
    u.standard_code          as condition_concept_code,
    u.condition_name,
    u.condition_start_date
from unioned u
join {{ ref('person') }} p
    on p.source = u.source
   and p.person_source_value = u.person_source_value
