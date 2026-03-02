from typing import NewType, TypedDict, TypeVar, Union, Generic
from dxpy import DXFile

### Type Hints ###
DXFileID = NewType("DXFileID", str)
DXProjectID = NewType("DXProjectID", str)
FlatDXLink = TypedDict("FlatDXLink", {'$dnanexus_link': DXFileID})
NestedDXLinkContent = TypedDict("NestedDXLinkContent", {'id': DXFileID, 'project': DXProjectID})
NestedDXLink = TypedDict("NestedDXLink", {'$dnanexus_link': NestedDXLinkContent})
DXLink = Union[FlatDXLink, NestedDXLink]
T = TypeVar("T", DXFile, DXLink)

class SompyJobOutput(TypedDict):
    stats_csv: DXFile

class SompyResults(TypedDict, Generic[T]):
    recall_plot: T
    sompy_csv: T