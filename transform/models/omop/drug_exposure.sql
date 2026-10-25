-- OMOP CDM drug_exposure (Synthea RxNorm meds).
with stg as (
    select * from {{ ref('stg_synthea__drug') }}
)
select
    row_number() over (order by s.person_source_value) as drug_exposure_id,
    p.person_id,
    s.source,
    s.source_code as drug_source_value,
    s.source_vocabulary,
    s.drug_name,
    s.drug_exposure_start_date
from stg s
join {{ ref('person') }} p
    on p.source = s.source
   and p.person_source_value = s.person_source_value
