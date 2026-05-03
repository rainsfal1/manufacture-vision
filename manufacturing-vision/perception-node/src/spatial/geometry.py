import cv2
import numpy as np

class PolygonZone:
    """
    Represents a spatial detection zone.
    Evaluates tracking bounding boxes using their footpoint.
    """
    def __init__(self, zone_id: str, coordinates: list, required_ppe: list = None):
        self.zone_id = zone_id
        self.required_ppe: list[str] = required_ppe or []
        # coordinates should be a list of [x, y] pairs
        self.polygon = np.array(coordinates, np.int32)
        # Reshape for cv2 polygon tests
        self.polygon = self.polygon.reshape((-1, 1, 2))

    def get_footpoint(self, bbox: list) -> tuple:
        """
        Calculates the footpoint (bottom-center) of a bounding box.
        bbox format: [x1, y1, x2, y2]
        """
        x1, y1, x2, y2 = bbox
        center_x = x1 + (x2 - x1) / 2
        bottom_y = y2
        return (int(center_x), int(bottom_y))

    def get_center(self, bbox: list) -> tuple:
        x1, y1, x2, y2 = bbox
        return (int(x1 + (x2 - x1) / 2), int(y1 + (y2 - y1) / 2))

    def check_zone(self, bbox: list) -> bool:
        """
        Returns True if the footpoint of the bounding box is inside the zone.
        """
        footpoint = self.get_footpoint(bbox)
        result = cv2.pointPolygonTest(self.polygon, footpoint, False)
        return result >= 0

    def check_zone_center(self, bbox: list) -> bool:
        """
        Returns True if the center of the bounding box is inside the zone.
        """
        center = self.get_center(bbox)
        result = cv2.pointPolygonTest(self.polygon, center, False)
        return result >= 0
