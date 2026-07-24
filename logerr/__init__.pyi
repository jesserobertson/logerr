"""Type stubs for logerr main module."""

from . import option as option
from . import result as result
from . import utilities as utilities
from .config import configure as configure
from .config import get_config as get_config
from .config import reset_config as reset_config
from .option import Nothing as Nothing
from .option import Option as Option
from .option import Some as Some
from .result import Err as Err
from .result import Ok as Ok
from .result import Result as Result

__version__: str

__all__ = [
    "Err",
    "Nothing",
    "Ok",
    "Option",
    "Result",
    "Some",
    "configure",
    "get_config",
    "option",
    "reset_config",
    "result",
    "utilities",
]
