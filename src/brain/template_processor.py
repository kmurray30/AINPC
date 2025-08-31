import json
import os
import sys
from typing import List



filename = os.path.splitext(os.path.basename(__file__))[0]
if __name__ == "__main__" or __name__ == filename: # If the script is being run directly
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))) # Adjust the path to the project root

from src.core.schemas.CollectionSchemas import Entity
from src.utils import Logger
from src.utils.Logger import Level
import yaml

Logger.set_level(Level.DEBUG)


# Take in an info template and convert it to a list of Entities
def template_to_entities_simple(template_path: str) -> List[Entity]:
    with open(template_path, "r") as f:
        template = yaml.safe_load(f)
    entities = []
    for item in template:
        entities.append(Entity(key=item, content=item, tags=[]))
    return entities


if __name__ == "__main__":
    entities = template_to_entities_simple("src/brain/example_template.yaml")
    Logger.debug(f"Entities: {entities}")