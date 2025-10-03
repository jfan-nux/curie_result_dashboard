select * from proddb.fionafan.coda_experiments_daily;

select * from  proddb.fionafan.coda_experiments_daily
where fetched_at = (select max(fetched_at) from proddb.fionafan.coda_experiments_daily)
and project_status in ('8. In experiment', '8. Ramping')
;


select * from proddb.fionafan.nux_curie_result_daily;