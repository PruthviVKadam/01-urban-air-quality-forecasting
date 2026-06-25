"""Feature engineering pipeline using DuckDB.

Transforms the normalized, long-format measurements and weather data into a wide,
feature-rich dataset suitable for forecasting models.
"""

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger("uaqf.modeling.features")


def build_features(data_dir: Path) -> Path:
    """Builds features.parquet from processed data."""
    processed_dir = data_dir / "processed"
    features_dir = data_dir / "features"
    features_dir.mkdir(parents=True, exist_ok=True)

    measurements_path = processed_dir / "measurements.parquet"
    weather_path = processed_dir / "weather.parquet"
    output_path = features_dir / "features.parquet"

    if not measurements_path.exists():
        logger.warning("No measurements found. Cannot build features.")
        return output_path

    con = duckdb.connect()
    try:
        # 1. Pivot measurements to wide format
        con.execute(
            f"CREATE OR REPLACE VIEW m_long AS SELECT * FROM read_parquet('{measurements_path.as_posix()}')"
        )

        # We need a list of pollutants dynamically or statically. We know our target pollutants: pm25, o3, no2
        # Pivot syntax: PIVOT m_long ON pollutant USING first(value) GROUP BY station_id, ts
        con.execute("""
            CREATE OR REPLACE VIEW m_wide AS 
            PIVOT m_long 
            ON pollutant IN ('pm25', 'o3', 'no2')
            USING first(value) 
            GROUP BY station_id, ts
        """)

        # Check if weather exists
        has_weather = weather_path.exists()
        if has_weather:
            con.execute(
                f"CREATE OR REPLACE VIEW w AS SELECT * FROM read_parquet('{weather_path.as_posix()}')"
            )
        else:
            con.execute(
                "CREATE OR REPLACE VIEW w AS SELECT '' as station_id, current_timestamp as ts, 0.0 as temperature_c, 0.0 as humidity_pct, 0.0 as wind_speed_ms, 0.0 as pressure_hpa WHERE 1=0"
            )

        # 2. Join & Extract Time Features
        # DuckDB has date_part('hour', ts) and date_part('isodow', ts) (1=Mon, 7=Sun)
        # To avoid division by zero or errors, ensure types are float
        con.execute("""
            CREATE OR REPLACE VIEW joined AS
            SELECT 
                m.station_id,
                m.ts,
                m.pm25,
                m.o3,
                m.no2,
                w.temperature_c,
                w.humidity_pct,
                w.wind_speed_ms,
                w.pressure_hpa,
                date_part('hour', m.ts) as hour_of_day,
                date_part('isodow', m.ts) as day_of_week
            FROM m_wide m
            LEFT JOIN w 
                ON m.station_id = w.station_id 
                AND m.ts = w.ts
        """)

        # 3. Add cyclical encodings & Lags
        # pi() is available in duckdb
        query = """
            SELECT 
                *,
                sin(hour_of_day * pi() / 12) as sin_hour,
                cos(hour_of_day * pi() / 12) as cos_hour,
                sin(day_of_week * pi() / 3.5) as sin_dow,
                cos(day_of_week * pi() / 3.5) as cos_dow,
                
                -- Lags for pm25
                lag(pm25, 1) OVER w_time as pm25_lag_1h,
                lag(pm25, 24) OVER w_time as pm25_lag_24h,
                avg(pm25) OVER w_roll_24 as pm25_roll_mean_24h,
                
                -- Lags for o3
                lag(o3, 1) OVER w_time as o3_lag_1h,
                lag(o3, 24) OVER w_time as o3_lag_24h,
                avg(o3) OVER w_roll_24 as o3_roll_mean_24h,
                
                -- Lags for no2
                lag(no2, 1) OVER w_time as no2_lag_1h,
                lag(no2, 24) OVER w_time as no2_lag_24h,
                avg(no2) OVER w_roll_24 as no2_roll_mean_24h
            FROM joined
            WINDOW 
                w_time AS (PARTITION BY station_id ORDER BY ts),
                w_roll_24 AS (PARTITION BY station_id ORDER BY ts ROWS BETWEEN 23 PRECEDING AND CURRENT ROW)
        """

        # Export to parquet
        logger.info("Writing features to parquet...")
        con.execute(f"COPY ({query}) TO '{output_path.as_posix()}' (FORMAT PARQUET)")

        # Get count
        count = con.execute(
            f"SELECT count(*) FROM read_parquet('{output_path.as_posix()}')"
        ).fetchone()[0]
        logger.info("features_built", extra={"rows": count, "path": output_path.as_posix()})

        return output_path
    finally:
        con.close()
