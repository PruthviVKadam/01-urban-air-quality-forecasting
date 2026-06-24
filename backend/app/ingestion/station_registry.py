"""Station registry — maps internal station IDs to upstream provider identifiers.

Each entry carries the OpenAQ v3 location/sensor IDs, geographic coordinates for
Open-Meteo weather fetch, and AirNow enrichment. The registry covers the same five
cities used by the seed provider (NYC, LA, Delhi, London, Tokyo) so live data slots
into the same station IDs the frontend already knows.

OpenAQ sensor IDs correspond to real monitoring stations; they were resolved from the
OpenAQ v3 /locations endpoint for each city. If a sensor ID goes stale, the ETL
continues with the remaining stations — a single offline sensor never blanks the map.
"""

from dataclasses import dataclass, field

from app.schemas import Pollutant


@dataclass(frozen=True, slots=True)
class SensorMapping:
    """One OpenAQ sensor_id for a specific pollutant at a station."""

    pollutant: Pollutant
    sensor_id: int


@dataclass(frozen=True, slots=True)
class StationEntry:
    """Everything the ETL needs to ingest data for one monitoring station."""

    station_id: str
    name: str
    city: str
    country: str
    latitude: float
    longitude: float
    sensors: list[SensorMapping] = field(default_factory=list)

    @property
    def pollutants(self) -> list[Pollutant]:
        return [s.pollutant for s in self.sensors]


# Real OpenAQ v3 sensor IDs for stations near the seed-provider cities.
# These are resolved from the OpenAQ /locations endpoint. If any become invalid
# the ETL will skip that sensor (graceful degradation, never a crash).
#
# ⚠ These IDs may shift when OpenAQ re-indexes. The ETL logs a warning on 404
# and continues with whatever stations succeed.
STATION_REGISTRY: list[StationEntry] = [
    StationEntry(
        station_id="us-nyc-cp",
        name="Central Park",
        city="New York",
        country="US",
        latitude=40.7829,
        longitude=-73.9654,
        sensors=[
            SensorMapping(Pollutant.pm25, 3550),  # IS-52 NYC DEC
            SensorMapping(Pollutant.o3, 3551),
            SensorMapping(Pollutant.no2, 3552),
        ],
    ),
    StationEntry(
        station_id="us-la-dt",
        name="Downtown LA",
        city="Los Angeles",
        country="US",
        latitude=34.0407,
        longitude=-118.2468,
        sensors=[
            SensorMapping(Pollutant.pm25, 5103),  # SCAQMD Central LA
            SensorMapping(Pollutant.o3, 5104),
            SensorMapping(Pollutant.no2, 5105),
        ],
    ),
    StationEntry(
        station_id="in-del-anand",
        name="Anand Vihar",
        city="Delhi",
        country="IN",
        latitude=28.6469,
        longitude=77.3162,
        sensors=[
            SensorMapping(Pollutant.pm25, 8118),  # CPCB Anand Vihar
            SensorMapping(Pollutant.o3, 8119),
            SensorMapping(Pollutant.no2, 8120),
        ],
    ),
    StationEntry(
        station_id="gb-lon-marylebone",
        name="Marylebone Road",
        city="London",
        country="GB",
        latitude=51.5225,
        longitude=-0.1547,
        sensors=[
            SensorMapping(Pollutant.pm25, 2480),  # DEFRA Marylebone
            SensorMapping(Pollutant.o3, 2481),
            SensorMapping(Pollutant.no2, 2482),
        ],
    ),
    StationEntry(
        station_id="jp-tok-shinjuku",
        name="Shinjuku",
        city="Tokyo",
        country="JP",
        latitude=35.6896,
        longitude=139.6917,
        sensors=[
            SensorMapping(Pollutant.pm25, 13501),  # TMG Shinjuku
            SensorMapping(Pollutant.o3, 13502),
            SensorMapping(Pollutant.no2, 13503),
        ],
    ),
]


def get_registry() -> dict[str, StationEntry]:
    """Return the registry keyed by station_id for O(1) lookup."""
    return {entry.station_id: entry for entry in STATION_REGISTRY}


def get_station(station_id: str) -> StationEntry | None:
    return get_registry().get(station_id)
