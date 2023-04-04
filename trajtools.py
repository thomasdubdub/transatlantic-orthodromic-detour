from traffic.data import opensky
from traffic.core import Traffic
from traffic.core import Flight
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiLineString
import pyproj

NM_TO_M = 1852


def traffic_from_opensky(
    start,
    stop,
    callsign=None,
    icao24=None,
    bounds=None,
    departure_airport=None,
    arrival_airport=None,
):
    return opensky.history(
        start,
        stop,
        callsign=callsign,
        icao24=icao24,
        bounds=bounds,
        departure_airport=departure_airport,
        arrival_airport=arrival_airport,
    )


def traffic_from_parquet(file_name):
    return Traffic.from_file(file_name)


def traffic_to_gdf(t):
    df = t.data.copy()
    df = df.dropna(subset=["callsign", "latitude", "longitude"])
    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="epsg:4326",
    )


def to_line_gdf(points_gdf):
    linestring = LineString(points_gdf["geometry"].tolist())
    multilinestring = MultiLineString([linestring])
    return gpd.GeoDataFrame(
        {"id": [0], "geometry": [multilinestring]}, crs=points_gdf.crs
    )


def flight_to_ortho(flight, rule="60S"):
    ortho = Flight(flight.data.iloc[[0, -1]])
    return ortho.resample(rule=rule, projection="lcc")


def great_circle_trajectory(lat1, lon1, lat2, lon2):
    g = pyproj.Geod(ellps="WGS84")
    (az12, az21, dist) = g.inv(lon1, lat1, lon2, lat2)
    lonlats = g.npts(lon1, lat1, lon2, lat2, 1 + int(dist / 1000))
    lonlats.insert(0, (lon1, lat1))
    lonlats.append((lon2, lat2))
    points = [Point(lon, lat) for lon, lat in lonlats]
    return gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")


def great_circle_distance(lat1, lon1, lat2, lon2):
    g = pyproj.Geod(ellps="WGS84")
    _, _, dist = g.inv(lon1, lat1, lon2, lat2)
    return dist


def ortho_distance(flight):
    f = flight.data.copy()
    f = f.dropna(subset=["latitude", "longitude"])
    return great_circle_distance(
        f.iloc[0].latitude,
        f.iloc[0].longitude,
        f.iloc[-1].latitude,
        f.iloc[-1].longitude,
    )


def cum_distance(flight, rule="30s", projection="lcc"):
    flight_r = flight.resample(rule=rule, projection=projection)
    return flight_r.cumulative_distance().data.iloc[-1].cumdist * NM_TO_M