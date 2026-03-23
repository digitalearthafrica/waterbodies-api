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
        WITH uids_from_wb_id AS (
            SELECT
                uid
            FROM
                waterbodies_historical_extent
            WHERE
                wb_id = {wb_id}
        ),
        wb AS (
            SELECT 
                uid, 
                area_m2 AS actual_area_m2 
            FROM 
                waterbodies_historical_extent
            WHERE uid = (SELECT uid FROM uids_from_wb_id LIMIT 1)
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
                percent_observed > 85 AND percent_invalid < 5
        )
        SELECT * from filtered_stats ORDER BY date
    """
    return query


WQ_COLUMNS = [
    "hue_q0_1",
    "hue_q0_2",
    "hue_q0_3",
    "hue_q0_4",
    "hue_q0_5",
    "hue_q0_6",
    "hue_q0_7",
    "hue_q0_8",
    "hue_q0_9",
    "owt_q0_1",
    "owt_q0_2",
    "owt_q0_3",
    "owt_q0_4",
    "owt_q0_5",
    "owt_q0_6",
    "owt_q0_7",
    "owt_q0_8",
    "owt_q0_9",
    "chla_q0_1",
    "chla_q0_2",
    "chla_q0_3",
    "chla_q0_4",
    "chla_q0_5",
    "chla_q0_6",
    "chla_q0_7",
    "chla_q0_8",
    "chla_q0_9",
    "tsi_q0_1",
    "tsi_q0_2",
    "tsi_q0_3",
    "tsi_q0_4",
    "tsi_q0_5",
    "tsi_q0_6",
    "tsi_q0_7",
    "tsi_q0_8",
    "tsi_q0_9",
    "tsm_q0_1",
    "tsm_q0_2",
    "tsm_q0_3",
    "tsm_q0_4",
    "tsm_q0_5",
    "tsm_q0_6",
    "tsm_q0_7",
    "tsm_q0_8",
    "tsm_q0_9",
    "st_max_q0_1",
    "st_max_q0_2",
    "st_max_q0_3",
    "st_max_q0_4",
    "st_max_q0_5",
    "st_max_q0_6",
    "st_max_q0_7",
    "st_max_q0_8",
    "st_max_q0_9",
    "st_median_q0_1",
    "st_median_q0_2",
    "st_median_q0_3",
    "st_median_q0_4",
    "st_median_q0_5",
    "st_median_q0_6",
    "st_median_q0_7",
    "st_median_q0_8",
    "st_median_q0_9",
    "st_min_q0_1",
    "st_min_q0_2",
    "st_min_q0_3",
    "st_min_q0_4",
    "st_min_q0_5",
    "st_min_q0_6",
    "st_min_q0_7",
    "st_min_q0_8",
    "st_min_q0_9",
    "fai_cover",
    "ndvi_cover",
]


def waterbody_water_quality_summary_query(wb_id: int, start_date: date, end_date: date):

    query = f"""
    WITH 
    uids_from_wb_id AS (
        SELECT uid
        FROM waterbodies_historical_extent
        WHERE wb_id = {wb_id}
    ), 
    wb AS (
        SELECT uid
        FROM waterbodies_historical_extent
        WHERE uid = (SELECT uid FROM uids_from_wb_id LIMIT 1)
    )
    SELECT date, {", ".join(WQ_COLUMNS)}                                       
    FROM waterbodies_water_quality as wq 
    INNER JOIN wb on wq.uid = wb.uid 
    WHERE wq.date BETWEEN '{start_date}' AND '{end_date}' ORDER BY date
    """
    return query


def waterbody_water_quality_maps_query(wb_id: int, start_date: date, end_date: date):
    query = f"""
    WITH 
    uids_from_wb_id AS (
        SELECT uid
        FROM waterbodies_historical_extent
        WHERE wb_id = {wb_id}
    ), 
    wb AS (
        SELECT uid
        FROM waterbodies_historical_extent
        WHERE uid = (SELECT uid FROM uids_from_wb_id LIMIT 1)
    )
    SELECT date, tsi_q0_5, tsm_q0_5, st_median_q0_5, fai_cover                         
    FROM waterbodies_water_quality as wq 
    INNER JOIN wb on wq.uid = wb.uid 
    WHERE wq.date BETWEEN '{start_date}' AND '{end_date}' ORDER BY date
    """
    return query


def all_waterbodies_water_quality_summaries(
    variables: list[str], start_date: date, end_date: date
):
    for variable in variables:
        assert variable in WQ_COLUMNS

    query = f"""
    SELECT uid, date, {", ".join(variables)}                    
    FROM waterbodies_water_quality as wq 
    INNER JOIN wb on wq.uid = wb.uid 
    WHERE wq.date BETWEEN '{start_date}' AND '{end_date}' ORDER BY date
    """
    return query
