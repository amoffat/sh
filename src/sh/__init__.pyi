"""
Type stubs for the sh module.

sh replaces itself in sys.modules with a SelfWrapper instance at import time,
so all attribute lookups (e.g. ``sh.ls``) are resolved dynamically and return
Command objects.  The module-level ``__getattr__`` below is the PEP 562
mechanism that tells type checkers about this dynamic resolution, enabling
patterns like ``from sh import ls`` to type-check cleanly.
"""

import _thread
import threading
from collections.abc import AsyncIterator, Callable, Generator, Iterable, Set
from contextlib import contextmanager
from queue import Queue
from types import GenericAlias, ModuleType, TracebackType
from typing import (
    IO,
    Any,
    ClassVar,
    Final,
    Generic,
    Literal,
    Protocol,
    Self,
    TypeAlias,
    overload,
    type_check_only,
)

from typing_extensions import TypeVar

_CommandIn: TypeAlias = (
    str | bytes | IO[Any] | Queue[Any] | RunningCommand | Iterable[Any]
)
_CommandOut: TypeAlias = str | int | IO[Any] | Callable[..., Any]
_CommandTarget: TypeAlias = bool | Literal["out", "err"]
_CommandOkCode: TypeAlias = int | list[int] | tuple[int, ...]
_CommandDone: TypeAlias = Callable[[RunningCommand, bool, int], None]
_CommandArgPreprocess: TypeAlias = Callable[..., tuple[list[Any], dict[str, Any]]]

# ---------------------------------------------------------------------------
# Version / metadata
# ---------------------------------------------------------------------------

__all__ = []
__version__: str
__project_url__: str
DEFAULT_ENCODING: str

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ForkException(Exception):
    def __init__(self, orig_exc: str) -> None: ...

@type_check_only
class ErrorReturnCodeMeta(type): ...

class ErrorReturnCode(Exception):
    __metaclass__: ClassVar = ErrorReturnCodeMeta

    exit_code: int
    full_cmd: str
    stdout: bytes
    stderr: bytes
    truncate: bool
    truncate_cap: int

    def __init__(
        self,
        full_cmd: str,
        stdout: bytes,
        stderr: bytes,
        truncate: bool = ...,
    ) -> None: ...

class SignalException(ErrorReturnCode): ...
class CommandNotFound(AttributeError): ...

# Concrete ErrorReturnCode subclasses for exit codes 0-255
class ErrorReturnCode_0(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_1(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_2(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_3(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_4(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_5(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_6(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_7(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_8(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_9(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_10(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_11(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_12(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_13(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_14(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_15(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_16(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_17(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_18(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_19(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_20(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_21(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_22(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_23(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_24(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_25(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_26(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_27(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_28(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_29(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_30(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_31(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_32(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_33(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_34(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_35(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_36(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_37(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_38(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_39(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_40(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_41(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_42(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_43(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_44(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_45(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_46(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_47(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_48(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_49(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_50(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_51(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_52(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_53(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_54(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_55(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_56(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_57(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_58(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_59(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_60(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_61(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_62(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_63(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_64(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_65(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_66(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_67(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_68(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_69(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_70(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_71(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_72(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_73(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_74(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_75(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_76(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_77(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_78(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_79(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_80(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_81(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_82(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_83(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_84(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_85(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_86(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_87(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_88(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_89(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_90(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_91(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_92(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_93(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_94(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_95(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_96(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_97(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_98(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_99(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_100(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_101(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_102(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_103(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_104(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_105(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_106(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_107(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_108(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_109(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_110(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_111(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_112(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_113(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_114(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_115(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_116(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_117(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_118(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_119(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_120(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_121(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_122(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_123(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_124(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_125(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_126(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_127(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_128(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_129(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_130(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_131(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_132(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_133(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_134(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_135(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_136(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_137(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_138(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_139(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_140(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_141(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_142(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_143(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_144(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_145(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_146(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_147(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_148(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_149(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_150(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_151(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_152(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_153(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_154(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_155(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_156(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_157(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_158(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_159(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_160(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_161(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_162(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_163(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_164(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_165(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_166(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_167(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_168(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_169(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_170(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_171(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_172(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_173(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_174(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_175(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_176(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_177(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_178(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_179(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_180(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_181(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_182(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_183(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_184(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_185(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_186(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_187(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_188(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_189(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_190(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_191(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_192(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_193(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_194(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_195(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_196(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_197(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_198(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_199(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_200(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_201(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_202(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_203(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_204(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_205(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_206(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_207(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_208(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_209(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_210(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_211(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_212(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_213(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_214(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_215(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_216(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_217(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_218(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_219(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_220(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_221(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_222(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_223(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_224(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_225(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_226(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_227(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_228(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_229(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_230(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_231(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_232(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_233(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_234(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_235(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_236(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_237(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_238(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_239(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_240(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_241(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_242(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_243(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_244(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_245(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_246(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_247(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_248(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_249(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_250(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_251(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_252(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_253(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_254(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...
class ErrorReturnCode_255(ErrorReturnCode, metaclass=ErrorReturnCodeMeta): ...

# Concrete SignalException subclasses for all known POSIX signals
class SignalException_SIGHUP(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGINT(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGQUIT(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGILL(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGTRAP(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGIOT(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGABRT(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGBUS(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGFPE(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGKILL(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGUSR1(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGSEGV(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGUSR2(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGPIPE(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGALRM(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGTERM(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGSTKFLT(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGCLD(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGCHLD(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGCONT(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGSTOP(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGTSTP(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGTTIN(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGTTOU(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGURG(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGXCPU(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGXFSZ(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGVTALRM(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGPROF(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGWINCH(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGIO(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGPOLL(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGPWR(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGSYS(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGRTMIN(SignalException, metaclass=ErrorReturnCodeMeta): ...
class SignalException_SIGRTMAX(SignalException, metaclass=ErrorReturnCodeMeta): ...

# Numeric aliases — SignalException_N mirrors the named form for the same signal
class SignalException_1(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGHUP
class SignalException_2(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGINT
class SignalException_3(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGQUIT
class SignalException_4(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGILL
class SignalException_5(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGTRAP
class SignalException_6(
    SignalException, metaclass=ErrorReturnCodeMeta
): ...  # SIGABRT / SIGIOT
class SignalException_7(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGBUS
class SignalException_8(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGFPE
class SignalException_9(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGKILL
class SignalException_10(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGUSR1
class SignalException_11(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGSEGV
class SignalException_12(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGUSR2
class SignalException_13(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGPIPE
class SignalException_14(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGALRM
class SignalException_15(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGTERM
class SignalException_16(
    SignalException, metaclass=ErrorReturnCodeMeta
): ...  # SIGSTKFLT
class SignalException_17(
    SignalException, metaclass=ErrorReturnCodeMeta
): ...  # SIGCHLD / SIGCLD
class SignalException_18(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGCONT
class SignalException_19(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGSTOP
class SignalException_20(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGTSTP
class SignalException_21(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGTTIN
class SignalException_22(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGTTOU
class SignalException_23(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGURG
class SignalException_24(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGXCPU
class SignalException_25(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGXFSZ
class SignalException_26(
    SignalException, metaclass=ErrorReturnCodeMeta
): ...  # SIGVTALRM
class SignalException_27(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGPROF
class SignalException_28(
    SignalException, metaclass=ErrorReturnCodeMeta
): ...  # SIGWINCH
class SignalException_29(
    SignalException, metaclass=ErrorReturnCodeMeta
): ...  # SIGIO / SIGPOLL
class SignalException_30(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGPWR
class SignalException_31(SignalException, metaclass=ErrorReturnCodeMeta): ...  # SIGSYS
class SignalException_34(
    SignalException, metaclass=ErrorReturnCodeMeta
): ...  # SIGRTMIN
class SignalException_64(
    SignalException, metaclass=ErrorReturnCodeMeta
): ...  # SIGRTMAX

class TimeoutException(Exception):
    exit_code: int | None
    full_cmd: str
    def __init__(self, exit_code: int | None, full_cmd: str) -> None: ...

# Internal exceptions exposed via the allowlist
class DoneReadingForever(Exception): ...
class NotYetReadyToRead(Exception): ...

@type_check_only
class OProc:
    """Manages fork/exec and I/O wiring for a child process (Open Process).

    Instantiated internally by RunningCommand; accessible via
    ``RunningCommand.process``.
    """

    # Redirect sentinels — pass as ``stderr`` to merge stderr into stdout, or
    # as the ``pipe`` argument to select which stream is piped.
    STDOUT: int  # -1
    STDERR: int  # -2

    # -- populated in the parent process after fork() --
    pid: int
    sid: int
    pgid: int
    cmd: list[str]
    call_args: dict[str, Any]
    exit_code: int | None
    timed_out: bool
    started: float
    ctty: str | None
    stdin: Any  # file-like object, Queue, or None

    def __init__(
        self,
        command: Any,  # RunningCommand (forward ref avoided to keep stub simple)
        parent_log: Any,
        cmd: list[str],
        stdin: Any,
        stdout: Any,
        stderr: Any,
        call_args: dict[str, Any],
        pipe: int,
        process_assign_lock: threading.Lock,
    ) -> None: ...
    def __repr__(self) -> str: ...

    # -- aggregated output (bytes) --
    @property
    def stdout(self) -> bytes: ...
    @property
    def stderr(self) -> bytes: ...

    # -- process group / session helpers --
    def get_pgid(self) -> int:
        """Return the *current* process group ID (may differ from self.pgid)."""
        ...
    def get_sid(self) -> int:
        """Return the *current* session ID (may differ from self.sid)."""
        ...

    # -- signal helpers --
    def signal(self, sig: int) -> None: ...
    def signal_group(self, sig: int) -> None: ...
    def kill(self) -> None: ...
    def kill_group(self) -> None: ...
    def terminate(self) -> None: ...

    # -- lifecycle --
    def is_alive(self) -> tuple[bool, int | None]:
        """Poll the child without blocking.

        Returns ``(alive, exit_code)``.  ``exit_code`` is ``None`` while the
        process is still running.
        """
        ...
    def wait(self) -> int:
        """Block until the process exits and return its exit code."""
        ...

    # -- buffering controls --
    def change_in_bufsize(self, buf: int) -> None: ...
    def change_out_bufsize(self, buf: int) -> None: ...
    def change_err_bufsize(self, buf: int) -> None: ...

    # some private properties accessed by the tests
    _pipe_queue: Queue

# ---------------------------------------------------------------------------
# RunningCommand — returned when a Command is called
#
# Inherits from str in this stub (not at runtime) so that type checkers
# expose the full str interface — e.g. .split(), .strip(), .startswith() —
# matching the dynamic delegation in RunningCommand.__getattr__.
# ---------------------------------------------------------------------------

class RunningCommand(str):
    ran: str
    cmd: list[str]
    call_args: dict[str, Any]
    process: OProc

    # proxied `process` attributes via `__getattr__` from `_OProc_attr_allowlist`
    # (stubtest would complain if we'd use methods and properties here)
    signal: Final[Callable[[int], None]]
    terminate: Final[Callable[[], None]]
    kill: Final[Callable[[], None]]
    kill_group: Final[Callable[[], None]]
    signal_group: Final[Callable[[int], None]]
    pid: Final[int]
    sid: Final[int]
    pgid: Final[int]
    ctty: Final[str | None]

    @property
    def stdout(self) -> bytes: ...
    @property
    def stderr(self) -> bytes: ...
    @property
    def exit_code(self) -> int: ...

    #
    def __init__(
        self,
        cmd: list[str],
        call_args: dict[str, Any],
        stdin: _CommandIn,
        stdout: _CommandOut,
        stderr: _CommandOut,
    ) -> None: ...

    #
    def wait(self, timeout: float | None = ...) -> RunningCommand: ...
    def is_alive(self) -> bool: ...
    def handle_command_exit_code(self, code: int) -> None: ...

    #
    def __int__(self) -> int: ...
    def __float__(self) -> float: ...

    #
    def __await__(self) -> Generator[Any, None, RunningCommand]: ...
    def __aiter__(self) -> AsyncIterator[str]: ...
    async def __anext__(self) -> str: ...

    #
    def __iter__(self) -> Self: ...
    def __next__(self) -> str: ...

    #
    def __enter__(self) -> None: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

# ---------------------------------------------------------------------------
# Command — represents an un-run system program
# ---------------------------------------------------------------------------

# A Command can return a `str`` or a `Running`` command, depending on if it was
# called with `_return_cmd` or not.
_ReturnT_co = TypeVar("_ReturnT_co", RunningCommand, str, covariant=True, default=str)

class Command(Generic[_ReturnT_co]):
    thread_local: ClassVar[_thread._local] = ...
    RunningCommandCls: ClassVar[type[RunningCommand]] = ...

    @classmethod
    def __class_getitem__(cls, item: Any, /) -> GenericAlias: ...
    def __init__(self, path: str, search_paths: list[str] | None = ...) -> None: ...

    # -----------------------------------------------------------------------
    # bake() overloads
    #
    # These kwargs mirror Command._call_args in __init__.py.
    # When adding or changing a special kwarg, update BOTH _call_args (runtime)
    # AND all overloads below (type checking).
    # -----------------------------------------------------------------------
    @overload
    def bake(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: Literal[True],
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn | None = ...,
        _out: _CommandOut | None = ...,
        _err: _CommandOut | None = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: bool = ...,
        _async: bool = ...,
        **kwargs: Any,
    ) -> Command[RunningCommand]: ...
    @overload
    def bake(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn | None = ...,
        _out: _CommandOut | None = ...,
        _err: _CommandOut | None = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: bool = ...,
        _async: Literal[True],
        **kwargs: Any,
    ) -> Command[RunningCommand]: ...
    @overload
    def bake(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn | None = ...,
        _out: _CommandOut = ...,
        _err: _CommandOut = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: Literal[True],
        _async: bool = ...,
        **kwargs: Any,
    ) -> Command[RunningCommand]: ...
    @overload
    def bake(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn | None = ...,
        _out: _CommandOut | None = ...,
        _err: _CommandOut | None = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: Literal[False],
        _async: bool = ...,
        **kwargs: Any,
    ) -> Command[str]: ...
    @overload
    def bake(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn = ...,
        _out: _CommandOut = ...,
        _err: _CommandOut = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: bool = ...,
        _async: bool = ...,
        **kwargs: Any,
    ) -> Command[_ReturnT_co]:
        """Return a new Command with arguments and/or special kwargs pre-baked.

        Baked arguments and special kwargs act as persistent defaults that are
        applied whenever the returned Command is called or baked further.
        Call-time arguments always override baked defaults.

        Positional args and regular keyword args (e.g. ``color="never"``) are
        forwarded to the program as command-line arguments.  Special kwargs
        (prefixed with ``_``) control sh's own behavior and are **not** passed
        to the program.

        Special kwargs
        --------------
        _fg : bool, default False
            Run the command in the foreground using ``os.spawnv``.  The
            current process's stdin/stdout/stderr are attached directly to the
            child, making it the terminal foreground process.  Most other
            special kwargs are ignored when ``_fg=True``.

        _bg : bool, default False
            Run the command in the background.  Returns immediately with a
            ``RunningCommand``; call ``.wait()`` to block until it finishes.

        _bg_exc : bool, default True
            When ``_bg=True``, automatically surface exceptions raised by the
            background command.  Set to ``False`` if you intend to call
            ``.wait()`` yourself and handle exceptions there.

        _with : bool, default False
            Mark this command as a ``with``-context prepend target.  Only
            needed when passing parameters to the context command, e.g.
            ``with sh.contrib.sudo(password="x", _with=True):``.

        _in : str | bytes | IO | Queue | RunningCommand | Iterable, default None
            Data to feed into the process's stdin.  Accepts a string, bytes,
            any file-like object, a ``Queue``, another ``RunningCommand``, or
            any iterable.

        _out : str | int | IO | Callable, default None
            Redirect stdout.  A string is treated as a filename; an int as a
            file descriptor; a file-like object receives write calls; a
            callable is invoked with each chunk/line of output.

        _err : str | int | IO | Callable, default None
            Redirect stderr.  Same semantics as ``_out``.

        _err_to_out : bool, default None
            When ``True``, duplicate the process's stdout file descriptor to
            stderr, so both streams go to the same destination.

        _in_bufsize : int, default 0
            Buffer size for stdin.  ``0`` = unbuffered, ``1`` = line-buffered,
            any other value = buffer of that many bytes.

        _out_bufsize : int, default 1
            Buffer size for stdout (same values as ``_in_bufsize``).

        _err_bufsize : int, default 1
            Buffer size for stderr (same values as ``_in_bufsize``).

        _internal_bufsize : int, default 3*1024**2
            Number of buffer *chunks* retained in sh's internal deque for
            stdout/stderr.  Not a byte count — the total bytes stored equals
            ``_internal_bufsize × bufsize``.

        _env : dict[str, str], default None
            Explicit environment for the child process.  If ``None``, the
            calling process's environment is inherited.  This dict is
            authoritative; to override a single variable, pass a copy of
            ``os.environ`` with the change applied.

        _piped : bool | "out" | "err", default None
            Signal that this command feeds its output into another command via
            a pipe.  The value selects which stream is piped (``True``/
            ``"out"`` for stdout, ``"err"`` for stderr).

        _iter : bool | "out" | "err", default None
            Enable iterable mode.  Iterate over the command's output
            line-by-line (or chunk-by-chunk) in a ``for`` loop.  ``True``/
            ``"out"`` iterates stdout; ``"err"`` iterates stderr.

        _iter_noblock : bool | "out" | "err", default None
            Like ``_iter``, but the loop does not block when no output is
            available.  Instead, ``errno.EWOULDBLOCK`` is yielded.

        _iter_poll_time : float, default 0.1
            Seconds to sleep between polls of the output queue when iterating.

        _ok_code : _CommandOkCode, default 0
            Exit code(s) considered successful.  If the process exits with a
            code not in this collection, an ``ErrorReturnCode`` is raised.
            Negative values represent signals (e.g. ``-9`` suppresses
            ``SIGKILL``).

        _cwd : str, default None
            Working directory for the child process.

        _long_sep : str | None, default "="
            Separator between a long argument's name and value (e.g. ``"="``
            produces ``--key=value``).  Pass ``None`` to emit name and value
            as separate arguments (``--key value``).

        _long_prefix : str, default "--"
            Prefix for long (keyword) arguments.  Change to ``"-"`` for
            programs that use single-dash long options.

        _tty_in : bool, default False
            Allocate a pseudo-TTY for stdin.  Required by programs that check
            whether stdin is a terminal (e.g. ``ssh``).

        _tty_out : bool, default True
            Allocate a pseudo-TTY for stdout.  Disable with ``_tty_out=False``
            to use a plain pipe instead.

        _unify_ttys : bool, default False
            Merge the stdin and stdout TTYs into a single pseudo-terminal.
            Required by some programs (e.g. SSH) that expect a single pty.

        _encoding : str, default locale encoding
            Character encoding used to decode the process's output.

        _decode_errors : str, default "strict"
            Error handler passed to ``bytes.decode()`` for output decoding.
            Any value valid for ``bytes.decode()`` is accepted (e.g.
            ``"ignore"``, ``"replace"``).

        _timeout : float, default None
            Maximum seconds to wait for the process.  If exceeded, the signal
            specified by ``_timeout_signal`` is sent.

        _timeout_signal : int, default signal.SIGKILL
            Signal sent to the process when ``_timeout`` is exceeded.

        _no_out : bool, default False
            Discard stdout; do not buffer it internally.  Useful for commands
            that produce large amounts of output you do not need.

        _no_err : bool, default False
            Discard stderr; do not buffer it internally.

        _no_pipe : bool, default False
            Tell sh that this command will never be used as a pipe source, so
            it should not fill the internal pipe buffer.

        _tee : bool | "out" | "err", default None
            When redirection is active, also copy the redirected stream into
            sh's internal buffers (tee-style).  ``True``/``"out"`` tees
            stdout; ``"err"`` tees stderr.

        _done : _CommandDone, default None
            Callback invoked when the process terminates, regardless of exit
            code.  Receives the ``RunningCommand`` instance, a success bool,
            and the integer exit code.  Any exception that would be raised is
            raised *after* the callback returns.

        _tty_size : tuple[int, int], default (24, 80)
            ``(rows, columns)`` of the stdout TTY.  Affects line-wrapping
            behaviour of programs that query terminal dimensions.

        _truncate_exc : bool, default True
            Whether to truncate long stdout/stderr output in exception
            messages.

        _preexec_fn : Callable[[], None], default None
            Called in the child process after ``fork()`` but before
            ``execv()``.  Advanced use only.

        _uid : int, default None
            User ID to assume in the child process before ``execv()``.
            Requires root privileges.

        _new_session : bool, default False
            Run the child in a new session (``os.setsid()``), detaching it
            from the parent's process group and controlling terminal.

        _new_group : bool, default False
            Run the child in a new process group (``os.setpgid()``).

        _arg_preprocess : Callable[..., tuple[list, dict]], default None
            Advanced hook to rewrite positional args and kwargs before they
            are compiled into command-line strings.  The callable receives
            ``(args, kwargs)`` and must return a ``(args, kwargs)`` tuple.
            Primarily used internally by sh's contrib wrappers.

        _log_msg : Callable[..., str], default None
            Customise the log header emitted by sh's logger.  The callable
            receives ``(ran, call_args, pid=None)`` and should return a
            string.

        _close_fds : bool, default True
            Close all inherited file descriptors in the child (except stdin,
            stdout, stderr).  Automatically enabled when ``_pass_fds`` is set.

        _pass_fds : Set[int], default set()
            Allowlist of integer file descriptors to keep open in the child.
            Setting this forces ``_close_fds`` to ``True``.

        _return_cmd : bool, default False
            Always return a ``RunningCommand`` object rather than a plain
            ``str``, even for commands that have already finished.

        _async : bool, default False
            Make the command awaitable.  Use with ``await`` or with
            ``_iter=True`` and ``async for`` to consume output asynchronously.
        """
        ...

    # -----------------------------------------------------------------------
    # __call__() overloads
    #
    # These kwargs mirror Command._call_args in __init__.py.
    # When adding or changing a special kwarg, update BOTH _call_args (runtime)
    # AND all overloads below (type checking).
    # -----------------------------------------------------------------------
    @overload
    def __call__(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: Literal[True],
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn | None = ...,
        _out: _CommandOut | None = ...,
        _err: _CommandOut | None = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: bool = ...,
        _async: bool = ...,
        **kwargs: Any,
    ) -> RunningCommand: ...
    @overload
    def __call__(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn | None = ...,
        _out: _CommandOut | None = ...,
        _err: _CommandOut | None = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: bool = ...,
        _async: Literal[True],
        **kwargs: Any,
    ) -> RunningCommand: ...
    @overload
    def __call__(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn | None = ...,
        _out: _CommandOut | None = ...,
        _err: _CommandOut | None = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: Literal[True],
        _async: bool = ...,
        **kwargs: Any,
    ) -> RunningCommand: ...
    @overload
    def __call__(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn | None = ...,
        _out: _CommandOut | None = ...,
        _err: _CommandOut | None = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: Literal[False],
        _async: bool = ...,
        **kwargs: Any,
    ) -> str: ...
    @overload
    def __call__(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: _CommandIn | None = ...,
        _out: _CommandOut | None = ...,
        _err: _CommandOut | None = ...,
        _err_to_out: bool | None = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: dict[str, str] | None = ...,
        _piped: _CommandTarget | None = ...,
        _iter: _CommandTarget | None = ...,
        _iter_noblock: _CommandTarget | None = ...,
        _iter_poll_time: float = ...,
        _ok_code: _CommandOkCode = ...,
        _cwd: str | None = ...,
        _long_sep: str | None = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: float | None = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: _CommandTarget | None = ...,
        _done: _CommandDone | None = ...,
        _tty_size: tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Callable[[], None] | None = ...,
        _uid: int | None = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: _CommandArgPreprocess | None = ...,
        _log_msg: Callable[..., str] | None = ...,
        _close_fds: bool = ...,
        _pass_fds: Set[int] = ...,
        _return_cmd: bool = ...,
        _async: bool = ...,
        **kwargs: Any,
    ) -> _ReturnT_co:
        """Run the command, returning its output.

        Positional args and regular keyword args (e.g. ``color="never"``) are
        compiled into command-line arguments and passed to the program.
        Special kwargs (prefixed with ``_``) control sh's behaviour and are
        **not** passed to the program.

        See ``bake()`` for full documentation of all special kwargs.
        """
        ...

    # some private properties accessed by the tests
    _path: str
    _call_args: dict[str, Any]

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __enter__(self) -> None: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    # sub-command access (e.g. git.log, docker.container.ls)
    def __getattribute__(self, name: str) -> Command[_ReturnT_co]: ...

# ---------------------------------------------------------------------------
# StreamBufferer — exposed via allowlist
# ---------------------------------------------------------------------------

class StreamBufferer:
    type: int
    encoding: str
    decode_errors: str
    def __init__(
        self,
        buffer_type: int,
        encoding: str = ...,
        decode_errors: str = ...,
    ) -> None: ...
    def change_buffering(self, new_type: int) -> None: ...
    def process(self, chunk: bytes) -> list[bytes]: ...
    def flush(self) -> list[bytes]: ...

# ---------------------------------------------------------------------------
# pushd — context manager for temporary directory changes
# ---------------------------------------------------------------------------

@contextmanager
def pushd(path: str) -> Generator[None]: ...

# ---------------------------------------------------------------------------
# glob — path expansion helper
# ---------------------------------------------------------------------------

def glob(path: str, *args: Any, **kwargs: Any) -> list[str]: ...

# The return value on this technically isn't correct, it should be the type of
# the sh module, but I don't know how to write that. # FIXME
def bake(**kwargs: Any) -> Command[str]: ...
def _aggregate_keywords(
    *,
    kwargs: dict[str, Any],
    sep: str,
    prefix: str,
    raw: bool = False,
) -> list[str]: ...

# ---------------------------------------------------------------------------
# contrib — namespace of pre-baked command wrappers
# ---------------------------------------------------------------------------

_FnT = TypeVar("_FnT", bound=Callable[[Command[Any]], Command[Any]])

@type_check_only
class _ContribWrapper(Protocol):
    def __call__(self, fn: _FnT) -> _FnT: ...

# `types.ModuleType.__getattr__` returns `Any`, so type-checkers will assume every
# `Contrib` attribute is `Any`.
@type_check_only
class Contrib(ModuleType):
    @classmethod
    def __call__(cls, name: str) -> _ContribWrapper: ...

contrib: Final[Contrib] = ...

# ---------------------------------------------------------------------------
# Module-level __getattr__
#
# This is the PEP 562 hook that tells type checkers (mypy, pyright, …) that
# any name resolved from this module — e.g. ``from sh import ls`` or
# ``sh.grep`` — is a Command object.  Without this, dynamic attribute access
# via SelfWrapper.__getattr__ would be invisible to static analysis.
#
# ErrorReturnCode_N (0-255) and SignalException_SIG* names are declared
# explicitly above (all standard POSIX signals) rather than relying on this fallback.
# ---------------------------------------------------------------------------

def __getattr__(name: str) -> Command[str]: ...
