-- Unified Curie experiment results query
-- Returns unpivoted format for ALL experiments (single or multiple treatments)
-- This query keeps data in its natural format without pivoting

WITH latest_results AS (
    -- Get all results and identify the latest dimension_value for each metric/dimension combination
    SELECT
        dear.*,  -- Select all columns from dimension_experiment_analysis_results
        tm.desired_direction AS metric_desired_direction,
        tm.description AS metric_description,
        tm.metric_spec AS metric_spec,
        -- Extract base dimension value (before any parentheses) for deduplication
        CASE 
            WHEN dear.dimension_value IS NULL THEN NULL
            WHEN POSITION('(' IN dear.dimension_value) > 0 
            THEN TRIM(SUBSTRING(dear.dimension_value, 1, POSITION('(' IN dear.dimension_value) - 1))
            ELSE dear.dimension_value
        END AS base_dimension_value,
        -- Rank to get latest result for each metric/dimension/base_dimension_value combination
        ROW_NUMBER() OVER (
            PARTITION BY 
                dear.metric_name,
                dear.dimension_name,
                CASE 
                    WHEN dear.dimension_value IS NULL THEN NULL
                    WHEN POSITION('(' IN dear.dimension_value) > 0 
                    THEN TRIM(SUBSTRING(dear.dimension_value, 1, POSITION('(' IN dear.dimension_value) - 1))
                    ELSE dear.dimension_value
                END,
                dear.variant_name
            ORDER BY dear.analyzed_at DESC
        ) AS rn
    FROM
        proddb.public.dimension_experiment_analysis_results dear
        LEFT JOIN CONFIGURATOR_PROD.PUBLIC.TALLEYRAND_METRICS tm ON dear.metric_name = tm.name
    WHERE
        dear.analysis_id = '{analysis_id}'
        AND dear.metric_name IS NOT NULL
)

-- Final output in unpivoted format
SELECT
    -- Core columns
    metric_name,
    COALESCE(dimension_name, 'overall') AS dimension_name,
    COALESCE(dimension_value, 'overall') AS dimension_cut_name,
    variant_name,
    metric_value,
    metric_impact_relative,
    p_value,
    
    -- Significance calculation
    CASE 
        WHEN p_value IS NULL THEN 'unknown'
        WHEN p_value < 0.05 THEN 
            CASE
                WHEN (metric_desired_direction = 'METRIC_DIRECTIONALITY_INCREASE' AND metric_impact_relative > 0) 
                  OR (metric_desired_direction = 'METRIC_DIRECTIONALITY_DECREASE' AND metric_impact_relative < 0) 
                THEN 'significant positive'
                ELSE 'significant negative'
            END
        WHEN p_value < 0.25 THEN 
            CASE
                WHEN (metric_desired_direction = 'METRIC_DIRECTIONALITY_INCREASE' AND metric_impact_relative > 0) 
                  OR (metric_desired_direction = 'METRIC_DIRECTIONALITY_DECREASE' AND metric_impact_relative < 0) 
                THEN 'directional positive'
                ELSE 'directional negative'
            END
        ELSE 'flat'
    END AS stat_sig,
    
    -- Extended columns (available for selection)
    metric_description AS metric_definition,  -- Using description from talleyrand_metrics
    metric_spec,  -- Metric specification from talleyrand_metrics
    NULL AS metric_category,    -- Not available in talleyrand_metrics
    NULL AS metric_subcategory, -- Not available in talleyrand_metrics
    NULL AS metric_importance,  -- Not available in talleyrand_metrics
    metric_desired_direction,
    exposures AS unit_count,
    exposures AS sample_size,
    NULL AS stddev,  -- Not available in this table
    metric_impact_absolute,
    metric_impact_absolute_lower_bound,
    metric_impact_absolute_upper_bound,
    metric_impact_relative_lower_bound,
    metric_impact_relative_upper_bound,
    metric_impact_relative_global_lift,
    metric_impact_absolute_global_lift,
    analyzed_at,
    experiment_id,
    analysis_name,
    analysis_id
FROM
    latest_results
WHERE
    rn = 1  -- Only use latest result for each metric/dimension/base_dimension_value
    AND metric_value IS NOT NULL  -- Ensure we have actual values
ORDER BY 
    metric_name,
    CASE WHEN dimension_cut_name = 'overall' THEN 0 ELSE 1 END,
    dimension_cut_name,
    -- More flexible variant ordering:
    -- 1. 'control' always first (if exists)
    -- 2. 'treatment' second (if exists)  
    -- 3. 'treatment_N' patterns ordered by N
    -- 4. All other variants alphabetically
    CASE 
        WHEN LOWER(variant_name) = 'control' THEN 0 
        WHEN LOWER(variant_name) = 'treatment' THEN 1
        WHEN LOWER(variant_name) LIKE 'treatment_%' THEN 
            CASE 
                WHEN REGEXP_SUBSTR(variant_name, '[0-9]+$') IS NOT NULL 
                THEN 1 + CAST(REGEXP_SUBSTR(variant_name, '[0-9]+$') AS INT)
                ELSE 2 -- treatment_ without number
            END
        ELSE 1000 -- Other variants will be sorted alphabetically after
    END,
    variant_name;
