-- Sample Queries for proddb.fionafan.coda_sample
-- Coda Q3 2025 Roadmap data with clean column names (no col_ prefix)

-- =============================================================================
-- 1. Check today's data
-- =============================================================================
SELECT 
    COUNT(*) as row_count,
    COUNT(DISTINCT project_name) as unique_projects
FROM proddb.fionafan.coda_sample
WHERE DATE(fetched_at) = CURRENT_DATE();


-- =============================================================================
-- 2. View all projects with Status Notes
-- =============================================================================
SELECT 
    project_name,
    project_status,
    status_notes,
    dris,
    kickoff_date,
    launch_date,
    updated_at
FROM proddb.fionafan.coda_sample
WHERE DATE(fetched_at) = CURRENT_DATE()
    AND status_notes IS NOT NULL
    AND status_notes != ''
ORDER BY updated_at DESC;


-- =============================================================================
-- 3. Active/In-Progress projects
-- =============================================================================
SELECT 
    project_name,
    project_status,
    status_notes,
    dris,
    launch_date,
    dv,
    curie_ios,
    mode_ios
FROM proddb.fionafan.coda_sample
WHERE DATE(fetched_at) = CURRENT_DATE()
    AND (
        project_status LIKE '%In Progress%' 
        OR project_status LIKE '%Testing%'
        OR project_status LIKE '%Active%'
    )
ORDER BY launch_date DESC;


-- =============================================================================
-- 4. Projects by status (today's snapshot)
-- =============================================================================
SELECT 
    project_status,
    COUNT(*) as count,
    LISTAGG(DISTINCT project_name, ', ') WITHIN GROUP (ORDER BY project_name) as projects
FROM proddb.fionafan.coda_sample
WHERE DATE(fetched_at) = CURRENT_DATE()
GROUP BY project_status
ORDER BY count DESC;


-- =============================================================================
-- 5. Projects with links (ready for analysis)
-- =============================================================================
SELECT 
    project_name,
    project_status,
    dris,
    CASE WHEN brief IS NOT NULL AND brief != '' THEN '✓' ELSE '✗' END as has_brief,
    CASE WHEN figma IS NOT NULL AND figma != '' THEN '✓' ELSE '✗' END as has_figma,
    CASE WHEN dv IS NOT NULL AND dv != '' THEN '✓' ELSE '✗' END as has_dv,
    CASE WHEN curie_ios IS NOT NULL AND curie_ios != '' THEN '✓' ELSE '✗' END as has_curie,
    dv,
    curie_ios
FROM proddb.fionafan.coda_sample
WHERE DATE(fetched_at) = CURRENT_DATE()
ORDER BY project_name;


-- =============================================================================
-- 6. Historical tracking - see how projects evolved
-- =============================================================================
SELECT 
    DATE(fetched_at) as date,
    project_name,
    project_status,
    status_notes,
    dris
FROM proddb.fionafan.coda_sample
WHERE project_name = 'Travel'  -- Replace with your project name
ORDER BY date DESC;


-- =============================================================================
-- 7. Data freshness check
-- =============================================================================
SELECT 
    DATE(fetched_at) as fetch_date,
    COUNT(*) as rows,
    MAX(updated_at) as latest_update,
    DATEDIFF('day', DATE(fetched_at), CURRENT_DATE()) as days_old
FROM proddb.fionafan.coda_sample
GROUP BY DATE(fetched_at)
ORDER BY fetch_date DESC
LIMIT 7;


-- =============================================================================
-- 8. Projects by quarter
-- =============================================================================
SELECT 
    planned_for,
    COUNT(*) as project_count,
    COUNT(CASE WHEN project_status LIKE '%Shipped%' THEN 1 END) as shipped,
    COUNT(CASE WHEN project_status LIKE '%In Progress%' THEN 1 END) as in_progress
FROM proddb.fionafan.coda_sample
WHERE DATE(fetched_at) = CURRENT_DATE()
GROUP BY planned_for
ORDER BY planned_for;


-- =============================================================================
-- 9. Projects by DRI
-- =============================================================================
SELECT 
    dris,
    COUNT(*) as total_projects,
    COUNT(CASE WHEN project_status LIKE '%In Progress%' THEN 1 END) as active,
    COUNT(CASE WHEN project_status LIKE '%Shipped%' THEN 1 END) as shipped
FROM proddb.fionafan.coda_sample
WHERE DATE(fetched_at) = CURRENT_DATE()
    AND dris IS NOT NULL 
    AND dris != ''
GROUP BY dris
ORDER BY total_projects DESC;


-- =============================================================================
-- 10. Full project details (for debugging)
-- =============================================================================
SELECT *
FROM proddb.fionafan.coda_sample
WHERE DATE(fetched_at) = CURRENT_DATE()
LIMIT 10;

