from typing import Any, Dict, Union, get_args, get_origin
import json
from typing import Dict, Type, TypeVar
from dataclasses import MISSING, is_dataclass, fields

from dacite import from_dict, Config
from dacite.exceptions import MissingValueError
from enum import Enum

T = TypeVar('T')

def _is_optional_type(field_type) -> bool:
    """Check if a type is Optional (i.e., Union[T, None]) including PEP 604 unions (T | None)."""
    origin = get_origin(field_type)
    if origin is None:
        return False
    args = get_args(field_type)
    return type(None) in args and len(args) == 2

def _unwrap_optional(field_type):
    """If Optional[T], return inner T; otherwise return field_type unchanged."""
    if _is_optional_type(field_type):
        inner_types = [t for t in get_args(field_type) if t is not type(None)]  # noqa: E721
        return inner_types[0] if inner_types else field_type
    return field_type

def extract_obj_from_json_str(response_raw: str, response_type: Type[T], trim: bool = True) -> T:
        # Note: Sometimes the response starts with ```json, other times it starts with json
        # Trim everything before the first '{' and after the last '}'
        if trim:
            response_trimmed = response_raw[response_raw.find("{"):response_raw.rfind("}")+1]
        else:
            response_trimmed = response_raw
        json_dict = json.loads(response_trimmed)
        return extract_obj_from_dict(json_dict, response_type)

def extract_obj_from_dict(dict: Dict, response_type: Type[T]) -> T:
    if get_origin(response_type) is list:
        # If the response_type is a list, recurse
        # First check if the list is empty
        if not dict:
            return []
        entry_type = get_args(response_type)[0]  # Get the type of list entries
        # Recursively process each item in the list
        return [extract_obj_from_dict(item, entry_type) for item in dict]
    # If the response_type is a dataclass, use from_dict to convert
    else:
        # Use dacite's from_dict to convert the dict to the dataclass
        return from_dict(data_class=response_type, data=dict, config=Config(cast=[Enum], strict=True))

# Must be a dataclass, dict, list, enum, or primitive type, and all nested types must be as well (no non-dataclass classes allowed)
def convert_to_dataclass(value: Any, field_type):
    # None handling
    if value is None:
        if _is_optional_type(field_type) or field_type is Any:
            return None
        raise TypeError(
            f"Received None value for field of type {field_type}. "
            f"If this is intended, use Optional[{field_type}] in the dataclass definition."
        )

    # Normalize Optional[T] -> T (we already handled None case above)
    field_type = _unwrap_optional(field_type)

    # typing.Any: accept value as-is
    if field_type is Any:
        return value

    # Enums (expect name string)
    if isinstance(field_type, type) and issubclass(field_type, Enum):
        if not isinstance(value, str):
            raise TypeError(f"Expected enum name for {field_type.__name__}, got {type(value).__name__}")
        try:
            return field_type[value]
        except KeyError:
            raise TypeError(f"Invalid enum name for {field_type.__name__}: {value!r}")

    # Dataclasses
    if isinstance(field_type, type) and hasattr(field_type, "__dataclass_fields__"):
        if not isinstance(value, dict):
            raise TypeError(f"Expected mapping for {field_type.__name__}, got {type(value).__name__}")
        return _dict_to_dataclass(value, field_type)

    # Generic aliases (List[T], Dict[K,V])
    origin = get_origin(field_type)
    if origin is list:
        (item_type,) = get_args(field_type)
        if not isinstance(value, list):
            raise TypeError(f"Expected list, got {type(value).__name__}")
        return [convert_to_dataclass(item, item_type) for item in value]

    if origin is dict:
        key_type, val_type = get_args(field_type)
        if not isinstance(value, dict):
            raise TypeError(f"Expected dict, got {type(value).__name__}")
        return {convert_to_dataclass(k, key_type): convert_to_dataclass(v, val_type) for k, v in value.items()}

    # Primitives (enforce types; keep bool distinct from int)
    if field_type in (str, int, float, bool):
        if field_type is bool:
            if type(value) is not bool:
                raise TypeError(f"Expected bool, got {type(value).__name__}: {value!r}")
        elif field_type is int:
            if type(value) is not int:
                raise TypeError(f"Expected int, got {type(value).__name__}: {value!r}")
        elif not isinstance(value, field_type):
            raise TypeError(f"Expected {field_type.__name__}, got {type(value).__name__}: {value!r}")
        return value

    # If it's a class type that isn't dataclass/enum/primitive/list/dict, reject it explicitly
    if isinstance(field_type, type):
        raise TypeError(
            f"Unsupported class type {field_type} — only dataclasses, Enums, lists, dicts, and primitives are allowed."
        )

    # Fallback (Any or similar)
    raise TypeError(
        f"Unexpected type {field_type} for value {value!r}. "
        "Only dataclasses, Enums, lists, dicts, and primitives are allowed."
    )

def _dict_to_dataclass(data_dict: Dict[str, Any], dataclass_type: Type[T]) -> T:
    """Convert a dictionary into a dataclass, handling nested types and required/missing fields."""
    processed = {}
    for f in fields(dataclass_type):
        ftype = f.type
        if f.name in data_dict:
            processed[f.name] = convert_to_dataclass(data_dict[f.name], ftype)
        else:
            # Missing: if not Optional and no default, raise MissingValueError (dacite-like)
            if not _is_optional_type(ftype) and f.default is MISSING and f.default_factory is MISSING:
                raise MissingValueError(f"missing required field: {f.name}")
            # else: let dataclass apply default / leave Optional unset
    return dataclass_type(**processed)

def obj_to_dict(data: Any) -> dict:
    """Convert a dataclass or dictionary to a dictionary, casting Enums to their names."""
    if is_dataclass(data):
        # If data is a dataclass, convert it to a dictionary
        return {f.name: obj_to_dict(getattr(data, f.name)) for f in fields(data)}
    elif isinstance(data, dict):
        # If data is a dictionary, cast all objects to dicts
        return {k: obj_to_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        # If data is a list, recursively convert each item to a dict
        return [obj_to_dict(item) for item in data]
    elif isinstance(data, Enum):
        # If data is an Enum, convert it to its name
        return data.name
    elif isinstance(data, (str, int, float, bool)):
        # If data is a primitive type, return it as is
        return data
    elif data is None:
        # If data is None, return None
        return None
    else:
        raise ValueError(f"All data must be either a dataclass, dictionary, list, or primitive type. Unsupported type: {type(data).__name__} -> {data!r}")

def cast_enums(obj: dict[str, Any]) -> dict[str, Any]:
    if isinstance(obj, Enum):
        return obj.name  # Cast Enum to its name
    elif isinstance(obj, list):
        return [cast_enums(item) for item in obj]  # Handle lists
    elif isinstance(obj, dict):
        return {key: cast_enums(value) for key, value in obj.items()}  # Handle dicts
    return obj  # Return other types as-is