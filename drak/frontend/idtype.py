from __future__ import annotations
from typing import List
from dataclasses import dataclass

@dataclass
class IdType:
    base_type: IdType
    dimensions: List[int]

    def __init__(self, base_type: IdType|str, dimensions: List[int] = []) -> None:
        self.base_type = base_type
        self.dimensions = dimensions

IntType = IdType('int')
BoolType = IdType('bool')