import os
import random
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Any
from utils.config import Config
from utils.logger import get_logger

logger = get_logger("GPXParser")


class GPXParser:
    """Helper utility for discovering, selecting, and parsing GPX test files."""

    GPX_DIR: Path = Config.PROJECT_ROOT / "GPX files"

    @classmethod
    def get_all_gpx_files(cls) -> List[Path]:
        """Discovers and returns all .gpx file paths in the GPX directory."""
        if not cls.GPX_DIR.exists():
            raise FileNotFoundError(f"GPX files directory not found at: {cls.GPX_DIR}")

        gpx_files = sorted(list(cls.GPX_DIR.glob("*.gpx")))
        if not gpx_files:
            raise FileNotFoundError(f"No .gpx files found in directory: {cls.GPX_DIR}")

        return gpx_files

    @classmethod
    def select_random_gpx(cls) -> Tuple[Path, Dict[str, Any]]:
        """
        Randomly selects one .gpx file from the GPX directory, parses its track/waypoint coordinates,
        validates geographic bounds, and returns the file path along with parsed metadata.
        """
        all_files = cls.get_all_gpx_files()
        selected_file = random.choice(all_files)
        metadata = cls.parse_gpx_file(selected_file)

        logger.info(
            f"TC-002 Selected GPX:\n"
            f"  Filename:     {selected_file.name}\n"
            f"  Path:         {selected_file.resolve()}\n"
            f"  Total Files:  {len(all_files)} available in pool\n"
            f"  Source Points: {metadata['point_count']}\n"
            f"  Lat Range:    [{metadata['min_lat']:.4f}, {metadata['max_lat']:.4f}]\n"
            f"  Lon Range:    [{metadata['min_lon']:.4f}, {metadata['max_lon']:.4f}]"
        )
        return selected_file, metadata

    @classmethod
    def parse_gpx_file(cls, file_path: Path) -> Dict[str, Any]:
        """
        Parses a GPX file XML structure and extracts all coordinates (lat/lon),
        validating that points fall within valid geographic bounds.
        """
        tree = ET.parse(str(file_path))
        root = tree.getroot()

        # Handle XML namespace dynamically
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        wpts = root.findall(f".//{ns}wpt")
        trkpts = root.findall(f".//{ns}trkpt")
        rtepts = root.findall(f".//{ns}rtept")

        raw_points = wpts or trkpts or rtepts
        if not raw_points:
            # Check without namespace fallback
            raw_points = root.findall(".//wpt") or root.findall(".//trkpt") or root.findall(".//rtept")

        coordinates: List[Tuple[float, float]] = []
        for pt in raw_points:
            lat_str = pt.attrib.get("lat")
            lon_str = pt.attrib.get("lon")
            if lat_str and lon_str:
                try:
                    lat = float(lat_str)
                    lon = float(lon_str)
                    # Geographic validation
                    if not (-90.0 <= lat <= 90.0):
                        raise ValueError(f"Invalid latitude '{lat}' in GPX file {file_path.name}")
                    if not (-180.0 <= lon <= 180.0):
                        raise ValueError(f"Invalid longitude '{lon}' in GPX file {file_path.name}")
                    coordinates.append((lat, lon))
                except ValueError as e:
                    logger.warning(f"Error parsing coordinate: {e}")

        if len(coordinates) < 2:
            raise AssertionError(
                f"Selected GPX file '{file_path.name}' contains fewer than 2 valid coordinates (found {len(coordinates)})."
            )

        lats = [c[0] for c in coordinates]
        lons = [c[1] for c in coordinates]

        return {
            "filename": file_path.name,
            "filepath": str(file_path.resolve()),
            "point_count": len(coordinates),
            "coordinates": coordinates,
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lon": min(lons),
            "max_lon": max(lons),
            "first_point": coordinates[0],
            "last_point": coordinates[-1]
        }
