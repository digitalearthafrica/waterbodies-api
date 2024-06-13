from datetime import date

def waterbody_observations_query(wb_id: int, start_date: date, end_date: date) -> str:
    """
    _summary_

    Parameters
    ----------
    wb_id : int
        Waterbody ID to get observations for.
    start_date : date
        Start date for observations. Must be in YYYY-MM-DD format.
    end_date : date
        End date for observations. Must be in YYYY-MM-DD format.

    Returns
    -------
    str
        Query to be passed to SQL connection. The query returns
        obs_date, obs_area_wet, obs_pc_wet, obs_area_dry, 
        obs_pc_dry, obs_area_invalid, obs_pc_invalid, obs_area, obs_pc
    """

    query = f"""
        WITH wb AS (
            SELECT 
                uid, 
                area_m2 AS actual_area_m2 
            FROM 
                waterbodies_historical_extent
            WHERE wb_id = {wb_id}
        ),
        wbo AS (
            SELECT 
                wo.*, 
                wb.actual_area_m2 
            FROM 
                waterbodies_observations AS wo 
            INNER JOIN 
                wb ON wo.uid = wb.uid 
            WHERE 
                wo.date BETWEEN '{start_date}' AND '{end_date}'
        ),
        waterbody_stats AS (
            SELECT 
                date, 
                SUM(area_wet_m2) AS area_wet_m2, 
                SUM(area_dry_m2) AS area_dry_m2, 
                SUM(area_invalid_m2) AS area_invalid_m2, 
                SUM(area_wet_m2 + area_dry_m2 + area_invalid_m2) AS area_observed_m2, 
                actual_area_m2 
            FROM 
                wbo 
            GROUP BY 
                date, actual_area_m2
        ), 
        waterbody_stats_pc AS (
            SELECT 
                date, 
                area_wet_m2, 
                (area_wet_m2/actual_area_m2) * 100 AS percent_wet, 
                area_dry_m2, 
                (area_dry_m2/actual_area_m2) * 100 AS percent_dry, 
                area_invalid_m2, 
                (area_invalid_m2/actual_area_m2) * 100 AS percent_invalid, 
                area_observed_m2, 
                (area_observed_m2/actual_area_m2) * 100 AS percent_observed 
            FROM 
                waterbody_stats
        ),
        filtered_stats AS (
            SELECT 
                * 
            FROM 
                waterbody_stats_pc 
            WHERE 
                percent_observed > 85 AND percent_invalid < 100
        )
        SELECT * from filtered_stats ORDER BY date
    """
    return query

def bbox_query(minx: float, miny: float, maxx: float, maxy: float) -> str:

    query = f"""
        SELECT 
            wb_id,
            ST_AsTWKB(geometry)
        FROM 
            waterbodies_historical_extent
        WHERE
            geometry && ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}, 4326)
    """

    return query