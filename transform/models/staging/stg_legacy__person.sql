-- Messy legacy export -> normalized person shape.
-- Cleans free-text sex, US-style dates, and noisy race values.
with raw as (
    select * from read_csv_auto('{{ var("legacy_csv") }}', header = true, all_varchar = true)
)
select distinct
    'legacy'                                          as source,
    MRN                                               as person_source_value,
    case trim(lower(PT_SEX))
        when 'm' then 'MALE'
        when 'male' then 'MALE'
        when 'f' then 'FEMALE'
        when 'female' then 'FEMALE'
    end                                               as gender,
    extract(year from try_strptime(DOB, ['%m/%d/%Y', '%m-%d-%Y'])) as year_of_birth,
    case
        when trim(upper(RACE_DESC)) in ('', 'UNK') then null
        else upper(substr(trim(RACE_DESC), 1, 1)) || lower(substr(trim(RACE_DESC), 2))
    end                                               as race,
    cast(null as varchar)                             as ethnicity
from raw
