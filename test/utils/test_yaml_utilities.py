# test_yaml_utilities.py
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from dacite.exceptions import MissingValueError

# Keep the ../../../ sys.path adjustment you requested
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.utils.io_utils import load_yaml_into_dataclass, save_to_yaml_file
from src.core.Constants import Role


# --- Test dataclasses ---

# Test 1 - Basic data types
@dataclass
class CustomClass1:
    field1: str
    field2: int


# Test 2 - Lists and Dicts
@dataclass
class CustomClass2:
    field1: str
    field2: List[int]
    field3: Dict[str, str]


# Test 3 - Nested dataclasses
@dataclass
class CustomClass3:
    field1: str
    field2: CustomClass1


# Test 4 - Complex nested structures
@dataclass
class CustomClass4:
    field1: str
    field2: List[CustomClass1]
    field3: Dict[str, CustomClass2]
    field4: CustomClass3


# Test 5 - Optional fields (with default)
@dataclass
class CustomClass5:
    field1: str
    field2: int = field(default=0)


# Test 6 - List of dataclasses
@dataclass
class CustomClass6:
    field1: str
    field2: int


# Test 11 - Empty list within a dataclass
@dataclass
class CustomClass11:
    field1: str
    field2: List[int]


# Test 13 - Enums
@dataclass
class CustomClass13:
    role: Role


# Test 14 - Optional (None-allowed) fields
@dataclass
class CustomClass14:
    field1: Optional[str]
    field2: Optional[List[int]]
    field3: Optional[bool]


# Test 15 - Wrong type for str
@dataclass
class CustomClass15:
    field1: str


# --- Helper ---

def _roundtrip(tmp_path: Path, data, return_type, filename: str = "data.yaml"):
    """
    Save `data` (dataclass instance, list, scalar, etc.) to YAML
    then load it back as `return_type`.
    """
    path = tmp_path / sys._getframe().f_code.co_name
    save_to_yaml_file(data, path)

    # DEBUG
    custom_temp_path = Path("temporary")
    if not custom_temp_path.exists():
        custom_temp_path.mkdir(parents=True, exist_ok=True)
    save_to_yaml_file(data, custom_temp_path / filename)  # Save to a known path for testing

    return load_yaml_into_dataclass(path, return_type)


# --- Tests (now object-instantiating for the positive cases) ---

def test_basic_types(tmp_path: Path):
    expected = CustomClass1(field1="value1", field2=2)
    actual = _roundtrip(tmp_path, expected, CustomClass1, filename=sys._getframe().f_code.co_name)
    assert actual == expected


def test_lists_and_dicts(tmp_path: Path):
    expected = CustomClass2(
        field1="value2",
        field2=[1, 2, 3],
        field3={"key1": "value1", "key2": "value2"},
    )
    actual = _roundtrip(tmp_path, expected, CustomClass2, filename=sys._getframe().f_code.co_name)
    assert actual == expected


def test_nested_dataclasses(tmp_path: Path):
    expected = CustomClass3(
        field1="value3",
        field2=CustomClass1(field1="nested_value", field2=3),
    )
    actual = _roundtrip(tmp_path, expected, CustomClass3, filename=sys._getframe().f_code.co_name)
    assert actual == expected


def test_complex_nested_structures(tmp_path: Path):
    expected = CustomClass4(
        field1="value4",
        field2=[
            CustomClass1(field1="nested_value1", field2=4),
            CustomClass1(field1="nested_value2", field2=5),
        ],
        field3={
            "key1": CustomClass2(
                field1="dict_value1",
                field2=[6, 7],
                field3={"key1": "dict_nested_value1", "key2": "dict_nested_value2"},
            ),
            "key2": CustomClass2(
                field1="dict_value2",
                field2=[8, 9],
                field3={"key1": "dict_nested_value3", "key2": "dict_nested_value4"},
            ),
        },
        field4=CustomClass3(
            field1="nested_value3",
            field2=CustomClass1(field1="nested_value4", field2=10),
        ),
    )
    actual = _roundtrip(tmp_path, expected, CustomClass4, filename=sys._getframe().f_code.co_name)
    assert actual == expected


def test_optional_fields_default_roundtrip(tmp_path: Path):
    # We can't "omit" a field when instantiating an object, so this test
    # verifies that a dataclass with a default value persists and reloads equal.
    expected = CustomClass5(field1="value5")  # field2 defaults to 0
    actual = _roundtrip(tmp_path, expected, CustomClass5, filename=sys._getframe().f_code.co_name)
    assert actual == expected
    assert actual.field2 == 0


def test_list_of_dataclasses(tmp_path: Path):
    expected: List[CustomClass6] = [
        CustomClass6(field1="value6_1", field2=1),
        CustomClass6(field1="value6_2", field2=2),
    ]
    actual = _roundtrip(tmp_path, expected, List[CustomClass6], filename=sys._getframe().f_code.co_name)
    assert actual == expected
    assert len(actual) == 2

def test_missing_fields_error(tmp_path: Path):
    # Keep as raw dict to generate invalid YAML for loader
    invalid = {"field1": "value1"}  # missing field2
    path = tmp_path / sys._getframe().f_code.co_name
    save_to_yaml_file(invalid, path)
    with pytest.raises(MissingValueError):
        _ = load_yaml_into_dataclass(path, CustomClass1)

def test_missing_fields_error_from_dict(tmp_path: Path):
    # Keep as raw dict to generate invalid YAML for loader
    invalid = {"field1": "value1"}  # missing field2
    path = tmp_path / sys._getframe().f_code.co_name
    save_to_yaml_file(invalid, path)
    with pytest.raises(MissingValueError):
        _ = load_yaml_into_dataclass(path, CustomClass1)

def test_none_type_for_non_optional_field(tmp_path: Path):
    # Keep as raw dict to generate invalid YAML for loader
    invalid = CustomClass3(
        field1="value3",
        field2=None)
    path = tmp_path / sys._getframe().f_code.co_name
    save_to_yaml_file(invalid, path)
    with pytest.raises(TypeError):
        _ = load_yaml_into_dataclass(path, CustomClass3)

def test_incorrect_types_error(tmp_path: Path):
    # Keep as raw dict to generate invalid YAML for loader
    invalid = {"field1": "value1", "field2": "not_an_int"}
    path = tmp_path / sys._getframe().f_code.co_name
    save_to_yaml_file(invalid, path)
    with pytest.raises(TypeError):
        _ = load_yaml_into_dataclass(path, CustomClass1)

def test_empty_dict_error(tmp_path: Path):
    # Keep as raw dict to generate invalid YAML for loader
    invalid = {}
    path = tmp_path / sys._getframe().f_code.co_name
    save_to_yaml_file(invalid, path)
    with pytest.raises(MissingValueError):
        _ = load_yaml_into_dataclass(path, CustomClass1)

def test_empty_list_for_list_of_dataclasses(tmp_path: Path):
    expected: List[CustomClass1] = []
    actual = _roundtrip(tmp_path, expected, List[CustomClass1], filename=sys._getframe().f_code.co_name)
    assert isinstance(actual, list)
    assert actual == []

def test_empty_list_within_dataclass(tmp_path: Path):
    expected = CustomClass11(field1="value11", field2=[])
    actual = _roundtrip(tmp_path, expected, CustomClass11, filename=sys._getframe().f_code.co_name)
    assert actual == expected
    assert actual.field2 == []


def test_primitive_types_scalar(tmp_path: Path):
    # Scalar roundtrip: save an int and load as int
    path = tmp_path / sys._getframe().f_code.co_name
    save_to_yaml_file(12, path)
    value = load_yaml_into_dataclass(path, int)
    assert value == 12


def test_enums_saved_as_name_roundtrip(tmp_path: Path):
    # Saving an object with an Enum; your saver should emit the enum NAME (e.g., "user"),
    # and the loader should reconstruct Role.user
    expected = CustomClass13(role=Role.user)
    actual = _roundtrip(tmp_path, expected, CustomClass13, filename=sys._getframe().f_code.co_name)
    assert actual == expected
    assert actual.role == Role.user


def test_optional_fields_allow_none(tmp_path: Path):
    expected = CustomClass14(field1=None, field2=[1, 2], field3=None)
    actual = _roundtrip(tmp_path, expected, CustomClass14, filename=sys._getframe().f_code.co_name)
    assert actual == expected
    assert actual.field1 is None
    assert actual.field3 is None


def test_wrong_type_list_instead_of_str(tmp_path: Path):
    # Keep as raw dict to generate invalid YAML for loader
    invalid = {"field1": ["value15_1", "value15_2"]}
    path = tmp_path / sys._getframe().f_code.co_name
    save_to_yaml_file(invalid, path)
    with pytest.raises(TypeError):
        _ = load_yaml_into_dataclass(path, CustomClass15)
