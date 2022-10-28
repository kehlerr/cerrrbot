from dataclasses import dataclass
from typing import Optional, Union, Dict, Any


@dataclass
class AppResponse:
    status: Union[int, bool]
    result_info: Optional[str] = ""
