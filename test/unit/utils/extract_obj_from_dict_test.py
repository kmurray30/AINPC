
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from dacite.exceptions import MissingValueError, WrongTypeError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.utils import parsing_utils, llm_utils
from src.core.Constants import Role

# Test 1 - Basic data types
@dataclass
class DataClass1:
    field1: str
    field2: int

test_data_1 = {
    "field1": "value1",
    "field2": 2
}

test_object_1 = parsing_utils.extract_obj_from_dict(test_data_1, DataClass1)
assert test_object_1.field1 == "value1"
assert test_object_1.field2 == 2
print(f"Test 1 - Basic data types: PASS")

# Test 2 - Lists and Dicts
@dataclass
class DataClass2:
    field1: str
    field2: List[int]
    field3: Dict[str, str]

test_data_2 = {
    "field1": "value2",
    "field2": [1, 2, 3],
    "field3": {"key1": "value1", "key2": "value2"}
}

test_object_2 = parsing_utils.extract_obj_from_dict(test_data_2, DataClass2)
assert test_object_2.field1 == "value2"
assert test_object_2.field2 == [1, 2, 3]
assert test_object_2.field3 == {"key1": "value1", "key2": "value2"}
print(f"Test 2 - Lists and Dicts: PASS")

# Test 3 - Nested dataclasses
@dataclass
class DataClass3:
    field1: str
    field2: DataClass1

test_data_3 = {
    "field1": "value3",
    "field2": {
        "field1": "nested_value",
        "field2": 3
    }
}

test_object_3 = parsing_utils.extract_obj_from_dict(test_data_3, DataClass3)
assert test_object_3.field1 == "value3"
assert test_object_3.field2.field1 == "nested_value"
assert test_object_3.field2.field2 == 3
print(f"Test 3 - Nested dataclasses: PASS")

# Test 4 - Complex nested structures
@dataclass
class DataClass4:
    field1: str
    field2: List[DataClass1]
    field3: Dict[str, DataClass2]
    field4: DataClass3

test_data_4 = {
    "field1": "value4",
    "field2": [
        {"field1": "nested_value1", "field2": 4},
        {"field1": "nested_value2", "field2": 5}
    ],
    "field3": {
        "key1": {
            "field1": "dict_value1",
            "field2": [6, 7],
            "field3": {"key1": "dict_nested_value1", "key2": "dict_nested_value2"}
        },
        "key2": {
            "field1": "dict_value2",
            "field2": [8, 9],
            "field3": {"key1": "dict_nested_value3", "key2": "dict_nested_value4"}
        }
    },
    "field4": {
        "field1": "nested_value3",
        "field2": {
            "field1": "nested_value4",
            "field2": 10
        }
    }
}

test_object_4 = parsing_utils.extract_obj_from_dict(test_data_4, DataClass4)
assert test_object_4.field1 == "value4"
assert len(test_object_4.field2) == 2
assert test_object_4.field2[0].field1 == "nested_value1"
assert test_object_4.field2[0].field2 == 4
assert test_object_4.field2[1].field1 == "nested_value2"
assert test_object_4.field2[1].field2 == 5
assert test_object_4.field3["key1"].field1 == "dict_value1"
assert test_object_4.field3["key1"].field2 == [6, 7]
assert test_object_4.field3["key1"].field3 == {"key1": "dict_nested_value1", "key2": "dict_nested_value2"}
assert test_object_4.field3["key2"].field1 == "dict_value2"
assert test_object_4.field3["key2"].field2 == [8, 9]
assert test_object_4.field3["key2"].field3 == {"key1": "dict_nested_value3", "key2": "dict_nested_value4"}
assert test_object_4.field4.field1 == "nested_value3"
assert test_object_4.field4.field2.field1 == "nested_value4"
assert test_object_4.field4.field2.field2 == 10
print(f"Test 4 - Complex nested structures: PASS")

# Test 5 - Optional fields
@dataclass
class DataClass5:
    field1: str
    field2: int = field(default=0)

test_data_5 = {
    "field1": "value5"
    # "field2" is optional and will default to 0
}

test_object_5 = parsing_utils.extract_obj_from_dict(test_data_5, DataClass5)
assert test_object_5.field1 == "value5"
assert test_object_5.field2 == 0
print(f"Test 5 - Optional fields: PASS")

# Test 6 - List of dataclasses
@dataclass
class DataClass6:
    field1: str
    field2: int

test_data_6 = [
    {"field1": "value6_1", "field2": 1},
    {"field1": "value6_2", "field2": 2}
]

test_object_6 = parsing_utils.extract_obj_from_dict(test_data_6, List[DataClass6])
assert len(test_object_6) == 2
assert test_object_6[0].field1 == "value6_1"
assert test_object_6[0].field2 == 1
assert test_object_6[1].field1 == "value6_2"
assert test_object_6[1].field2 == 2
print(f"Test 6 - List of dataclasses: PASS")

# Test 7 - Validate that missing fields raise an error
try:
    test_data_1_invalid = {
        "field1": "value1"
        # "field2" is missing
    }
    test_object_1_invalid = parsing_utils.extract_obj_from_dict(test_data_1_invalid, DataClass1)
    raise TypeError("Test 7 failed: Missing fields did not raise an error")
except MissingValueError as e:
    print(f"Test 7 - Missing fields error: PASS")

# Test 8 - Validate that incorrect types raise an error
try:
    test_data_1_invalid_type = {
        "field1": "value1",
        "field2": "not_an_int"  # Incorrect type
    }
    test_object_1_invalid_type = parsing_utils.extract_obj_from_dict(test_data_1_invalid_type, DataClass1)
    raise TypeError("Test 8 failed: Incorrect types did not raise an error")
except WrongTypeError as e:
    print(f"Test 8 - Incorrect types error: PASS")

# Test 9 - Empty dict for dataclass
try:
    test_data_9 = {}
    test_object_9 = parsing_utils.extract_obj_from_dict(test_data_9, DataClass1)
    raise TypeError("Test 9 failed: Empty dict did not raise an error")
except MissingValueError as e:
    print(f"Test 9 - Empty dict error: PASS")

# Test 10 - Empty list for list of dataclasses
test_data_10 = []
test_object_10 = parsing_utils.extract_obj_from_dict(test_data_10, List[DataClass1])
assert len(test_object_10) == 0
print(f"Test 10 - Empty list for list of dataclasses: PASS")

# Test 11 - Empty list within a dataclass
@dataclass
class DataClass11:
    field1: str
    field2: List[int]

test_data_11 = {
    "field1": "value11",
    "field2": []
}

test_object_11 = parsing_utils.extract_obj_from_dict(test_data_11, DataClass11)
assert test_object_11.field1 == "value11"
assert len(test_object_11.field2) == 0
print(f"Test 11 - Empty list within a dataclass: PASS")

# Test 12 - Primitive types
test_data_12 = "12"

test_object_12 = llm_utils.extract_obj_from_llm_response(test_data_12, int)
assert test_object_12 == 12
print(f"Test 12 - Primitive types: PASS")

# Test 13 - Enums
@dataclass
class DataClass13:
    role: Role

test_data_13 = {
    "role": "user"
}
test_object_13 = parsing_utils.extract_obj_from_dict(test_data_13, DataClass13)
assert test_object_13.role == Role.user
print(f"Test 13 - Enums: PASS")

# Test 14 - None values are allowed with optional fields
@dataclass
class DataClass14:
    field1: Optional[str]
    field2: Optional[List[int]]
    field3: Optional[bool]
    
test_data_14 = {
    "field1": None,
    "field2": [1, 2],
    "field3": None
}

test_object_14 = parsing_utils.extract_obj_from_dict(test_data_14, DataClass14)
assert test_object_14.field1 is None
assert test_object_14.field2 == [1, 2]
assert test_object_14.field3 is None
print(f"Test 14 - None values are allowed with optional fields: PASS")

# Test 15 - Fails if expected str but got list of str
@dataclass
class DataClass15:
    field1: str

test_data_15 = {
    "field1": ["value15_1", "value15_2"]  # Incorrect type
}

try:
    test_object_15 = parsing_utils.extract_obj_from_dict(test_data_15, DataClass15)
    raise TypeError("Test 15 failed: Incorrect types did not raise an error")
except WrongTypeError as e:
    print(f"Test 15 - Incorrect types error: PASS")

print("All tests passed successfully!")