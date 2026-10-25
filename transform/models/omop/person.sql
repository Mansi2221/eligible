-- OMOP CDM person. Unifies both sources and assigns a surrogate person_id.
-- Downstream clinical tables join back on (source, person_source_value).
with unioned as (
    select * from {{ ref('stg_synthea__person') }}
    union all
    select * from {{ ref('stg_legacy__person') }}
)
select
    row_number() over (order by source, person_source_value) as person_id,
    source,
    person_source_value,
    gender,
    year_of_birth,
    race,
    ethnicity
from unioned
