select * from proddb.fionafan.coda_experiments_daily;

select * from  proddb.fionafan.coda_experiments_daily
where fetched_at = (select max(fetched_at) from proddb.fionafan.coda_experiments_daily)
and project_status in ('8. In experiment', '8. Ramping')
limit 1
;

select * from  proddb.fionafan.nux_curie_result_daily
where fetched_at = (select max(fetched_at) from proddb.fionafan.nux_curie_result_daily)
and project_status in ('8. In experiment', '8. Ramping')
limit 1
;

select analysis_name, count(1) from proddb.fionafan.nux_curie_result_daily group by analysis_name;
select * from proddb.fionafan.nux_curie_result_daily  where analysis_name = 'speed_store_card_and_row_experiment__ios_Users';

select view_name as view_name1,* from proddb.fionafan.coda_experiments_all_views;

SELECT view_name, COUNT(*) 
FROM proddb.fionafan.coda_experiments_all_views 
GROUP BY view_name;

select view_name, count(1) from proddb.fionafan.coda_experiments_focused group by view_name;
--  where view_name = 'Concluded xps';

select project_name, count(distinct) from proddb.fionafan.coda_experiments_focused where project_name = 'LiteGuests';


select project_name, count(distinct analysis_name) from proddb.fionafan.nux_curie_result_daily 
where fetched_at = (select max(fetched_at) from proddb.fionafan.nux_curie_result_daily) group by all ;

-- truncate table proddb.fionafan.nux_curie_result_daily;

select  id,name, description, compute_spec:lookBackPeriod as lookBackPeriod, 
compute_spec:lookBackUnit as lookBackUnit, compute_spec:snowflakeSpec:sql as sql, compute_spec:triggerSpec as lookBackPeriod
  , 'https://ops.doordash.team/decision-systems/unified-metrics-platform/sources/'||id as url
  from  CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_SOURCE where name = 'consumer_volume_curie' limit 100;
select * from proddb.fionafan.nux_curie_result_daily 
where fetched_at = (select max(fetched_at) from proddb.fionafan.nux_curie_result_daily) ;


select *, metric_spec:simpleParam:measure:name as measure_name, metric_spec:simpleParam:measure:sourceId as source_id 
from CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_METRICS where name = 'nux_onboarding_page_att_view' limit 100;
select distinct metric_spec:type as type from CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_METRICS group by all;
{
  "simpleParam": {
    "aggregation": "AGGREGATION_TYPE_SUM",
    "measure": {
      "id": "d4d04291-ba2f-4508-85ca-b8a11bee8c81",
      "name": "cross_platform_orders",
      "sourceId": "455ec10a-240c-4428-9540-b1e741811ace"
    }
  },
  "type": "METRIC_TYPE_SIMPLE"
}
{
  "simpleParam": {
    "aggregation": "AGGREGATION_TYPE_COUNT_DISTINCT",
    "measure": {
      "id": "55cf289f-cd78-43e7-9218-e4f3472cb605",
      "name": "page_att_view_device_id",
      "sourceId": "b458a2c6-c7ab-445f-a976-08f0397e7b3b"
    }
  },
  "type": "METRIC_TYPE_SIMPLE"
}
{
  "ratioParam": {
    "denominatorAggregation": "AGGREGATION_TYPE_NULL_IF_ZERO_COUNT_DISTINCT",
    "denominatorMeasure": {
      "id": "0431609e-2abc-4886-8cb6-701b748a255b",
      "name": "explore_page_visit_day"
    },
    "denominatorType": "DENOMINATOR_TYPE_MEASURE",
    "numeratorAggregation": "AGGREGATION_TYPE_COUNT_DISTINCT",
    "numeratorMeasure": {
      "id": "d3ab4060-2f73-4956-8d93-d20d3e72fec5",
      "name": "system_checkout_success_day"
    }
  },
  "type": "METRIC_TYPE_RATIO"
}


SELECT
  name,
  window_params:numeratorWindow:lowerBound::INT   AS numerator_lower_bound,
  window_params:numeratorWindow:upperBound::INT   AS numerator_upper_bound,
  window_params:numeratorWindow:windowUnit::STRING AS numerator_unit,
  window_params:denominatorWindow:lowerBound::INT AS denominator_lower_bound,
  window_params:denominatorWindow:upperBound::INT AS denominator_upper_bound,
  window_params:denominatorWindow:windowUnit::STRING AS denominator_unit
FROM CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_METRICS
WHERE name = 'consumers_mau';

CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_METRICS;

select * from configurator_prod.public.talleyrand_measures where id = 'd3ab4060-2f73-4956-8d93-d20d3e72fec5';

select * from proddb.fionafan.nux_curie_result_daily 
where  analysis_id = '775207ad-2e6d-4283-8e77-6aee61253ce3'
and metric_name = 'webx_conversion_rate';

