select 'Senegal' as pays, 'UEMOA' as zone
-- Guillemets doubles : BigQuery n'accepte pas l'échappement par
-- apostrophe redoublée du SQL standard.
union all select "Cote d'Ivoire", 'UEMOA'
union all select 'Mali', 'UEMOA'
union all select 'Burkina Faso', 'UEMOA'
union all select 'Benin', 'UEMOA'
union all select 'Togo', 'UEMOA'
union all select 'Nigeria', 'ZMAO'
union all select 'Ghana', 'ZMAO'
