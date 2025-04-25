import json
from enum import Enum

# Custom JSON encoder for Enums
class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name  # Serialize the enum as its name (e.g., "PASS")
        return super().default(obj)