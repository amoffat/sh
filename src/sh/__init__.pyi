"""
Type stubs for the sh module.

sh replaces itself in sys.modules with a SelfWrapper instance at import time,
so all attribute lookups (e.g. ``sh.ls``) are resolved dynamically and return
Command objects.  The module-level ``__getattr__`` below is the PEP 562
mechanism that tells type checkers about this dynamic resolution, enabling
patterns like ``from sh import ls`` to type-check cleanly.
"""

import threading
from contextlib import contextmanager
from queue import Queue
from typing import (
    AbstractSet,
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generator,
    Generic,
    IO,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    overload,
)

from typing_extensions import TypeVar as _TypeVarExt

# ---------------------------------------------------------------------------
# Version / metadata
# ---------------------------------------------------------------------------

__version__: str
__project_url__: str
DEFAULT_ENCODING: str

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ForkException(Exception):
    def __init__(self, orig_exc: str) -> None: ...

class ErrorReturnCode(Exception):
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
class ErrorReturnCode_0(ErrorReturnCode): ...
class ErrorReturnCode_1(ErrorReturnCode): ...
class ErrorReturnCode_2(ErrorReturnCode): ...
class ErrorReturnCode_3(ErrorReturnCode): ...
class ErrorReturnCode_4(ErrorReturnCode): ...
class ErrorReturnCode_5(ErrorReturnCode): ...
class ErrorReturnCode_6(ErrorReturnCode): ...
class ErrorReturnCode_7(ErrorReturnCode): ...
class ErrorReturnCode_8(ErrorReturnCode): ...
class ErrorReturnCode_9(ErrorReturnCode): ...
class ErrorReturnCode_10(ErrorReturnCode): ...
class ErrorReturnCode_11(ErrorReturnCode): ...
class ErrorReturnCode_12(ErrorReturnCode): ...
class ErrorReturnCode_13(ErrorReturnCode): ...
class ErrorReturnCode_14(ErrorReturnCode): ...
class ErrorReturnCode_15(ErrorReturnCode): ...
class ErrorReturnCode_16(ErrorReturnCode): ...
class ErrorReturnCode_17(ErrorReturnCode): ...
class ErrorReturnCode_18(ErrorReturnCode): ...
class ErrorReturnCode_19(ErrorReturnCode): ...
class ErrorReturnCode_20(ErrorReturnCode): ...
class ErrorReturnCode_21(ErrorReturnCode): ...
class ErrorReturnCode_22(ErrorReturnCode): ...
class ErrorReturnCode_23(ErrorReturnCode): ...
class ErrorReturnCode_24(ErrorReturnCode): ...
class ErrorReturnCode_25(ErrorReturnCode): ...
class ErrorReturnCode_26(ErrorReturnCode): ...
class ErrorReturnCode_27(ErrorReturnCode): ...
class ErrorReturnCode_28(ErrorReturnCode): ...
class ErrorReturnCode_29(ErrorReturnCode): ...
class ErrorReturnCode_30(ErrorReturnCode): ...
class ErrorReturnCode_31(ErrorReturnCode): ...
class ErrorReturnCode_32(ErrorReturnCode): ...
class ErrorReturnCode_33(ErrorReturnCode): ...
class ErrorReturnCode_34(ErrorReturnCode): ...
class ErrorReturnCode_35(ErrorReturnCode): ...
class ErrorReturnCode_36(ErrorReturnCode): ...
class ErrorReturnCode_37(ErrorReturnCode): ...
class ErrorReturnCode_38(ErrorReturnCode): ...
class ErrorReturnCode_39(ErrorReturnCode): ...
class ErrorReturnCode_40(ErrorReturnCode): ...
class ErrorReturnCode_41(ErrorReturnCode): ...
class ErrorReturnCode_42(ErrorReturnCode): ...
class ErrorReturnCode_43(ErrorReturnCode): ...
class ErrorReturnCode_44(ErrorReturnCode): ...
class ErrorReturnCode_45(ErrorReturnCode): ...
class ErrorReturnCode_46(ErrorReturnCode): ...
class ErrorReturnCode_47(ErrorReturnCode): ...
class ErrorReturnCode_48(ErrorReturnCode): ...
class ErrorReturnCode_49(ErrorReturnCode): ...
class ErrorReturnCode_50(ErrorReturnCode): ...
class ErrorReturnCode_51(ErrorReturnCode): ...
class ErrorReturnCode_52(ErrorReturnCode): ...
class ErrorReturnCode_53(ErrorReturnCode): ...
class ErrorReturnCode_54(ErrorReturnCode): ...
class ErrorReturnCode_55(ErrorReturnCode): ...
class ErrorReturnCode_56(ErrorReturnCode): ...
class ErrorReturnCode_57(ErrorReturnCode): ...
class ErrorReturnCode_58(ErrorReturnCode): ...
class ErrorReturnCode_59(ErrorReturnCode): ...
class ErrorReturnCode_60(ErrorReturnCode): ...
class ErrorReturnCode_61(ErrorReturnCode): ...
class ErrorReturnCode_62(ErrorReturnCode): ...
class ErrorReturnCode_63(ErrorReturnCode): ...
class ErrorReturnCode_64(ErrorReturnCode): ...
class ErrorReturnCode_65(ErrorReturnCode): ...
class ErrorReturnCode_66(ErrorReturnCode): ...
class ErrorReturnCode_67(ErrorReturnCode): ...
class ErrorReturnCode_68(ErrorReturnCode): ...
class ErrorReturnCode_69(ErrorReturnCode): ...
class ErrorReturnCode_70(ErrorReturnCode): ...
class ErrorReturnCode_71(ErrorReturnCode): ...
class ErrorReturnCode_72(ErrorReturnCode): ...
class ErrorReturnCode_73(ErrorReturnCode): ...
class ErrorReturnCode_74(ErrorReturnCode): ...
class ErrorReturnCode_75(ErrorReturnCode): ...
class ErrorReturnCode_76(ErrorReturnCode): ...
class ErrorReturnCode_77(ErrorReturnCode): ...
class ErrorReturnCode_78(ErrorReturnCode): ...
class ErrorReturnCode_79(ErrorReturnCode): ...
class ErrorReturnCode_80(ErrorReturnCode): ...
class ErrorReturnCode_81(ErrorReturnCode): ...
class ErrorReturnCode_82(ErrorReturnCode): ...
class ErrorReturnCode_83(ErrorReturnCode): ...
class ErrorReturnCode_84(ErrorReturnCode): ...
class ErrorReturnCode_85(ErrorReturnCode): ...
class ErrorReturnCode_86(ErrorReturnCode): ...
class ErrorReturnCode_87(ErrorReturnCode): ...
class ErrorReturnCode_88(ErrorReturnCode): ...
class ErrorReturnCode_89(ErrorReturnCode): ...
class ErrorReturnCode_90(ErrorReturnCode): ...
class ErrorReturnCode_91(ErrorReturnCode): ...
class ErrorReturnCode_92(ErrorReturnCode): ...
class ErrorReturnCode_93(ErrorReturnCode): ...
class ErrorReturnCode_94(ErrorReturnCode): ...
class ErrorReturnCode_95(ErrorReturnCode): ...
class ErrorReturnCode_96(ErrorReturnCode): ...
class ErrorReturnCode_97(ErrorReturnCode): ...
class ErrorReturnCode_98(ErrorReturnCode): ...
class ErrorReturnCode_99(ErrorReturnCode): ...
class ErrorReturnCode_100(ErrorReturnCode): ...
class ErrorReturnCode_101(ErrorReturnCode): ...
class ErrorReturnCode_102(ErrorReturnCode): ...
class ErrorReturnCode_103(ErrorReturnCode): ...
class ErrorReturnCode_104(ErrorReturnCode): ...
class ErrorReturnCode_105(ErrorReturnCode): ...
class ErrorReturnCode_106(ErrorReturnCode): ...
class ErrorReturnCode_107(ErrorReturnCode): ...
class ErrorReturnCode_108(ErrorReturnCode): ...
class ErrorReturnCode_109(ErrorReturnCode): ...
class ErrorReturnCode_110(ErrorReturnCode): ...
class ErrorReturnCode_111(ErrorReturnCode): ...
class ErrorReturnCode_112(ErrorReturnCode): ...
class ErrorReturnCode_113(ErrorReturnCode): ...
class ErrorReturnCode_114(ErrorReturnCode): ...
class ErrorReturnCode_115(ErrorReturnCode): ...
class ErrorReturnCode_116(ErrorReturnCode): ...
class ErrorReturnCode_117(ErrorReturnCode): ...
class ErrorReturnCode_118(ErrorReturnCode): ...
class ErrorReturnCode_119(ErrorReturnCode): ...
class ErrorReturnCode_120(ErrorReturnCode): ...
class ErrorReturnCode_121(ErrorReturnCode): ...
class ErrorReturnCode_122(ErrorReturnCode): ...
class ErrorReturnCode_123(ErrorReturnCode): ...
class ErrorReturnCode_124(ErrorReturnCode): ...
class ErrorReturnCode_125(ErrorReturnCode): ...
class ErrorReturnCode_126(ErrorReturnCode): ...
class ErrorReturnCode_127(ErrorReturnCode): ...
class ErrorReturnCode_128(ErrorReturnCode): ...
class ErrorReturnCode_129(ErrorReturnCode): ...
class ErrorReturnCode_130(ErrorReturnCode): ...
class ErrorReturnCode_131(ErrorReturnCode): ...
class ErrorReturnCode_132(ErrorReturnCode): ...
class ErrorReturnCode_133(ErrorReturnCode): ...
class ErrorReturnCode_134(ErrorReturnCode): ...
class ErrorReturnCode_135(ErrorReturnCode): ...
class ErrorReturnCode_136(ErrorReturnCode): ...
class ErrorReturnCode_137(ErrorReturnCode): ...
class ErrorReturnCode_138(ErrorReturnCode): ...
class ErrorReturnCode_139(ErrorReturnCode): ...
class ErrorReturnCode_140(ErrorReturnCode): ...
class ErrorReturnCode_141(ErrorReturnCode): ...
class ErrorReturnCode_142(ErrorReturnCode): ...
class ErrorReturnCode_143(ErrorReturnCode): ...
class ErrorReturnCode_144(ErrorReturnCode): ...
class ErrorReturnCode_145(ErrorReturnCode): ...
class ErrorReturnCode_146(ErrorReturnCode): ...
class ErrorReturnCode_147(ErrorReturnCode): ...
class ErrorReturnCode_148(ErrorReturnCode): ...
class ErrorReturnCode_149(ErrorReturnCode): ...
class ErrorReturnCode_150(ErrorReturnCode): ...
class ErrorReturnCode_151(ErrorReturnCode): ...
class ErrorReturnCode_152(ErrorReturnCode): ...
class ErrorReturnCode_153(ErrorReturnCode): ...
class ErrorReturnCode_154(ErrorReturnCode): ...
class ErrorReturnCode_155(ErrorReturnCode): ...
class ErrorReturnCode_156(ErrorReturnCode): ...
class ErrorReturnCode_157(ErrorReturnCode): ...
class ErrorReturnCode_158(ErrorReturnCode): ...
class ErrorReturnCode_159(ErrorReturnCode): ...
class ErrorReturnCode_160(ErrorReturnCode): ...
class ErrorReturnCode_161(ErrorReturnCode): ...
class ErrorReturnCode_162(ErrorReturnCode): ...
class ErrorReturnCode_163(ErrorReturnCode): ...
class ErrorReturnCode_164(ErrorReturnCode): ...
class ErrorReturnCode_165(ErrorReturnCode): ...
class ErrorReturnCode_166(ErrorReturnCode): ...
class ErrorReturnCode_167(ErrorReturnCode): ...
class ErrorReturnCode_168(ErrorReturnCode): ...
class ErrorReturnCode_169(ErrorReturnCode): ...
class ErrorReturnCode_170(ErrorReturnCode): ...
class ErrorReturnCode_171(ErrorReturnCode): ...
class ErrorReturnCode_172(ErrorReturnCode): ...
class ErrorReturnCode_173(ErrorReturnCode): ...
class ErrorReturnCode_174(ErrorReturnCode): ...
class ErrorReturnCode_175(ErrorReturnCode): ...
class ErrorReturnCode_176(ErrorReturnCode): ...
class ErrorReturnCode_177(ErrorReturnCode): ...
class ErrorReturnCode_178(ErrorReturnCode): ...
class ErrorReturnCode_179(ErrorReturnCode): ...
class ErrorReturnCode_180(ErrorReturnCode): ...
class ErrorReturnCode_181(ErrorReturnCode): ...
class ErrorReturnCode_182(ErrorReturnCode): ...
class ErrorReturnCode_183(ErrorReturnCode): ...
class ErrorReturnCode_184(ErrorReturnCode): ...
class ErrorReturnCode_185(ErrorReturnCode): ...
class ErrorReturnCode_186(ErrorReturnCode): ...
class ErrorReturnCode_187(ErrorReturnCode): ...
class ErrorReturnCode_188(ErrorReturnCode): ...
class ErrorReturnCode_189(ErrorReturnCode): ...
class ErrorReturnCode_190(ErrorReturnCode): ...
class ErrorReturnCode_191(ErrorReturnCode): ...
class ErrorReturnCode_192(ErrorReturnCode): ...
class ErrorReturnCode_193(ErrorReturnCode): ...
class ErrorReturnCode_194(ErrorReturnCode): ...
class ErrorReturnCode_195(ErrorReturnCode): ...
class ErrorReturnCode_196(ErrorReturnCode): ...
class ErrorReturnCode_197(ErrorReturnCode): ...
class ErrorReturnCode_198(ErrorReturnCode): ...
class ErrorReturnCode_199(ErrorReturnCode): ...
class ErrorReturnCode_200(ErrorReturnCode): ...
class ErrorReturnCode_201(ErrorReturnCode): ...
class ErrorReturnCode_202(ErrorReturnCode): ...
class ErrorReturnCode_203(ErrorReturnCode): ...
class ErrorReturnCode_204(ErrorReturnCode): ...
class ErrorReturnCode_205(ErrorReturnCode): ...
class ErrorReturnCode_206(ErrorReturnCode): ...
class ErrorReturnCode_207(ErrorReturnCode): ...
class ErrorReturnCode_208(ErrorReturnCode): ...
class ErrorReturnCode_209(ErrorReturnCode): ...
class ErrorReturnCode_210(ErrorReturnCode): ...
class ErrorReturnCode_211(ErrorReturnCode): ...
class ErrorReturnCode_212(ErrorReturnCode): ...
class ErrorReturnCode_213(ErrorReturnCode): ...
class ErrorReturnCode_214(ErrorReturnCode): ...
class ErrorReturnCode_215(ErrorReturnCode): ...
class ErrorReturnCode_216(ErrorReturnCode): ...
class ErrorReturnCode_217(ErrorReturnCode): ...
class ErrorReturnCode_218(ErrorReturnCode): ...
class ErrorReturnCode_219(ErrorReturnCode): ...
class ErrorReturnCode_220(ErrorReturnCode): ...
class ErrorReturnCode_221(ErrorReturnCode): ...
class ErrorReturnCode_222(ErrorReturnCode): ...
class ErrorReturnCode_223(ErrorReturnCode): ...
class ErrorReturnCode_224(ErrorReturnCode): ...
class ErrorReturnCode_225(ErrorReturnCode): ...
class ErrorReturnCode_226(ErrorReturnCode): ...
class ErrorReturnCode_227(ErrorReturnCode): ...
class ErrorReturnCode_228(ErrorReturnCode): ...
class ErrorReturnCode_229(ErrorReturnCode): ...
class ErrorReturnCode_230(ErrorReturnCode): ...
class ErrorReturnCode_231(ErrorReturnCode): ...
class ErrorReturnCode_232(ErrorReturnCode): ...
class ErrorReturnCode_233(ErrorReturnCode): ...
class ErrorReturnCode_234(ErrorReturnCode): ...
class ErrorReturnCode_235(ErrorReturnCode): ...
class ErrorReturnCode_236(ErrorReturnCode): ...
class ErrorReturnCode_237(ErrorReturnCode): ...
class ErrorReturnCode_238(ErrorReturnCode): ...
class ErrorReturnCode_239(ErrorReturnCode): ...
class ErrorReturnCode_240(ErrorReturnCode): ...
class ErrorReturnCode_241(ErrorReturnCode): ...
class ErrorReturnCode_242(ErrorReturnCode): ...
class ErrorReturnCode_243(ErrorReturnCode): ...
class ErrorReturnCode_244(ErrorReturnCode): ...
class ErrorReturnCode_245(ErrorReturnCode): ...
class ErrorReturnCode_246(ErrorReturnCode): ...
class ErrorReturnCode_247(ErrorReturnCode): ...
class ErrorReturnCode_248(ErrorReturnCode): ...
class ErrorReturnCode_249(ErrorReturnCode): ...
class ErrorReturnCode_250(ErrorReturnCode): ...
class ErrorReturnCode_251(ErrorReturnCode): ...
class ErrorReturnCode_252(ErrorReturnCode): ...
class ErrorReturnCode_253(ErrorReturnCode): ...
class ErrorReturnCode_254(ErrorReturnCode): ...
class ErrorReturnCode_255(ErrorReturnCode): ...

# Concrete SignalException subclasses for all known POSIX signals
class SignalException_SIGHUP(SignalException): ...
class SignalException_SIGINT(SignalException): ...
class SignalException_SIGQUIT(SignalException): ...
class SignalException_SIGILL(SignalException): ...
class SignalException_SIGTRAP(SignalException): ...
class SignalException_SIGIOT(SignalException): ...
class SignalException_SIGABRT(SignalException): ...
class SignalException_SIGBUS(SignalException): ...
class SignalException_SIGFPE(SignalException): ...
class SignalException_SIGKILL(SignalException): ...
class SignalException_SIGUSR1(SignalException): ...
class SignalException_SIGSEGV(SignalException): ...
class SignalException_SIGUSR2(SignalException): ...
class SignalException_SIGPIPE(SignalException): ...
class SignalException_SIGALRM(SignalException): ...
class SignalException_SIGTERM(SignalException): ...
class SignalException_SIGSTKFLT(SignalException): ...
class SignalException_SIGCLD(SignalException): ...
class SignalException_SIGCHLD(SignalException): ...
class SignalException_SIGCONT(SignalException): ...
class SignalException_SIGSTOP(SignalException): ...
class SignalException_SIGTSTP(SignalException): ...
class SignalException_SIGTTIN(SignalException): ...
class SignalException_SIGTTOU(SignalException): ...
class SignalException_SIGURG(SignalException): ...
class SignalException_SIGXCPU(SignalException): ...
class SignalException_SIGXFSZ(SignalException): ...
class SignalException_SIGVTALRM(SignalException): ...
class SignalException_SIGPROF(SignalException): ...
class SignalException_SIGWINCH(SignalException): ...
class SignalException_SIGIO(SignalException): ...
class SignalException_SIGPOLL(SignalException): ...
class SignalException_SIGPWR(SignalException): ...
class SignalException_SIGSYS(SignalException): ...
class SignalException_SIGRTMIN(SignalException): ...
class SignalException_SIGRTMAX(SignalException): ...

# Numeric aliases — SignalException_N mirrors the named form for the same signal
class SignalException_1(SignalException): ...  # SIGHUP
class SignalException_2(SignalException): ...  # SIGINT
class SignalException_3(SignalException): ...  # SIGQUIT
class SignalException_4(SignalException): ...  # SIGILL
class SignalException_5(SignalException): ...  # SIGTRAP
class SignalException_6(SignalException): ...  # SIGABRT / SIGIOT
class SignalException_7(SignalException): ...  # SIGBUS
class SignalException_8(SignalException): ...  # SIGFPE
class SignalException_9(SignalException): ...  # SIGKILL
class SignalException_10(SignalException): ...  # SIGUSR1
class SignalException_11(SignalException): ...  # SIGSEGV
class SignalException_12(SignalException): ...  # SIGUSR2
class SignalException_13(SignalException): ...  # SIGPIPE
class SignalException_14(SignalException): ...  # SIGALRM
class SignalException_15(SignalException): ...  # SIGTERM
class SignalException_16(SignalException): ...  # SIGSTKFLT
class SignalException_17(SignalException): ...  # SIGCHLD / SIGCLD
class SignalException_18(SignalException): ...  # SIGCONT
class SignalException_19(SignalException): ...  # SIGSTOP
class SignalException_20(SignalException): ...  # SIGTSTP
class SignalException_21(SignalException): ...  # SIGTTIN
class SignalException_22(SignalException): ...  # SIGTTOU
class SignalException_23(SignalException): ...  # SIGURG
class SignalException_24(SignalException): ...  # SIGXCPU
class SignalException_25(SignalException): ...  # SIGXFSZ
class SignalException_26(SignalException): ...  # SIGVTALRM
class SignalException_27(SignalException): ...  # SIGPROF
class SignalException_28(SignalException): ...  # SIGWINCH
class SignalException_29(SignalException): ...  # SIGIO / SIGPOLL
class SignalException_30(SignalException): ...  # SIGPWR
class SignalException_31(SignalException): ...  # SIGSYS
class SignalException_34(SignalException): ...  # SIGRTMIN
class SignalException_64(SignalException): ...  # SIGRTMAX

class TimeoutException(Exception):
    exit_code: Optional[int]
    full_cmd: str
    def __init__(self, exit_code: Optional[int], full_cmd: str) -> None: ...

# Internal exceptions exposed via the allowlist
class DoneReadingForever(Exception): ...
class NotYetReadyToRead(Exception): ...

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
    cmd: List[str]
    call_args: Dict[str, Any]
    exit_code: Optional[int]
    timed_out: bool
    started: float
    ctty: Optional[str]
    stdin: Any  # file-like object, Queue, or None

    def __init__(
        self,
        command: Any,  # RunningCommand (forward ref avoided to keep stub simple)
        parent_log: Any,
        cmd: List[str],
        stdin: Any,
        stdout: Any,
        stderr: Any,
        call_args: Dict[str, Any],
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
    def is_alive(self) -> Tuple[bool, Optional[int]]:
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
    call_args: Dict[str, Any]
    cmd: List[str]
    process: OProc

    @property
    def stdout(self) -> bytes: ...
    @property
    def stderr(self) -> bytes: ...
    @property
    def exit_code(self) -> int: ...
    @property
    def pid(self) -> int: ...
    def wait(self, timeout: Optional[float] = ...) -> "RunningCommand": ...
    def is_alive(self) -> bool: ...
    def kill(self) -> None: ...
    def kill_group(self) -> None: ...
    def terminate(self) -> None: ...
    def signal(self, sig: int) -> None: ...
    def signal_group(self, sig: int) -> None: ...
    def __int__(self) -> int: ...
    def __float__(self) -> float: ...
    def __long__(self) -> int: ...
    def __await__(self) -> Generator[Any, None, "RunningCommand"]: ...
    def __aiter__(self) -> AsyncIterator[str]: ...
    def __enter__(self) -> None: ...
    def __exit__(self, *args: Any) -> None: ...
    def __next__(self) -> str: ...

# ---------------------------------------------------------------------------
# Command — represents an un-run system program
# ---------------------------------------------------------------------------

# A Command can return a `str`` or a `Running`` command, depending on if it was
# called with `_return_cmd` or not.
_ReturnT_co = _TypeVarExt(
    "_ReturnT_co", RunningCommand, str, covariant=True, default=str
)

class Command(Generic[_ReturnT_co]):
    def __init__(self, name: str, search_paths: Optional[List[str]] = ...) -> None: ...

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
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
        _return_cmd: bool = ...,
        _async: bool = ...,
        **kwargs: Any,
    ) -> "Command[RunningCommand]": ...
    @overload
    def bake(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
        _return_cmd: bool = ...,
        _async: Literal[True],
        **kwargs: Any,
    ) -> "Command[RunningCommand]": ...
    @overload
    def bake(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
        _return_cmd: Literal[True],
        _async: bool = ...,
        **kwargs: Any,
    ) -> "Command[RunningCommand]": ...
    @overload
    def bake(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
        _return_cmd: Literal[False],
        _async: bool = ...,
        **kwargs: Any,
    ) -> "Command[str]": ...
    @overload
    def bake(
        self,
        *args: Any,
        _fg: bool = ...,
        _bg: bool = ...,
        _bg_exc: bool = ...,
        _with: bool = ...,
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
        _return_cmd: bool = ...,
        _async: bool = ...,
        **kwargs: Any,
    ) -> "Command[_ReturnT_co]":
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

        _ok_code : int | list[int] | tuple[int, ...], default 0
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

        _done : Callable[[RunningCommand, bool, int], None], default None
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

        _pass_fds : AbstractSet[int], default set()
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
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
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
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
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
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
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
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
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
        _in: Optional[
            Union[str, bytes, IO[Any], "Queue[Any]", RunningCommand, Iterable[Any]]
        ] = ...,
        _out: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err: Optional[Union[str, int, IO[Any], Callable[..., Any]]] = ...,
        _err_to_out: Optional[bool] = ...,
        _in_bufsize: int = ...,
        _out_bufsize: int = ...,
        _err_bufsize: int = ...,
        _internal_bufsize: int = ...,
        _env: Optional[Dict[str, str]] = ...,
        _piped: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_noblock: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _iter_poll_time: float = ...,
        _ok_code: Union[int, List[int], Tuple[int, ...]] = ...,
        _cwd: Optional[str] = ...,
        _long_sep: Optional[str] = ...,
        _long_prefix: str = ...,
        _tty_in: bool = ...,
        _tty_out: bool = ...,
        _unify_ttys: bool = ...,
        _encoding: str = ...,
        _decode_errors: str = ...,
        _timeout: Optional[float] = ...,
        _timeout_signal: int = ...,
        _no_out: bool = ...,
        _no_err: bool = ...,
        _no_pipe: bool = ...,
        _tee: Optional[Union[bool, Literal["out", "err"]]] = ...,
        _done: Optional[Callable[["RunningCommand", bool, int], None]] = ...,
        _tty_size: Tuple[int, int] = ...,
        _truncate_exc: bool = ...,
        _preexec_fn: Optional[Callable[[], None]] = ...,
        _uid: Optional[int] = ...,
        _new_session: bool = ...,
        _new_group: bool = ...,
        _arg_preprocess: Optional[
            Callable[..., Tuple[List[Any], Dict[str, Any]]]
        ] = ...,
        _log_msg: Optional[Callable[..., str]] = ...,
        _close_fds: bool = ...,
        _pass_fds: AbstractSet[int] = ...,
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
    _call_args: Dict[str, Any]

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __enter__(self) -> None: ...
    def __exit__(self, *args: Any) -> None: ...
    # sub-command access (e.g. git.log, docker.container.ls)
    def __getattr__(self, name: str) -> "Command[_ReturnT_co]": ...

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
    def process(self, chunk: bytes) -> List[bytes]: ...
    def flush(self) -> List[bytes]: ...

# ---------------------------------------------------------------------------
# pushd — context manager for temporary directory changes
# ---------------------------------------------------------------------------

@contextmanager
def pushd(path: str) -> Iterator[None]: ...

# ---------------------------------------------------------------------------
# glob — path expansion helper
# ---------------------------------------------------------------------------

def glob(path: str, *args: Any, **kwargs: Any) -> List[str]: ...

# The return value on this technically isn't correct, it should be the type of
# the sh module, but I don't know how to write that. # FIXME
def bake(*args: Any, **kwargs: Any) -> Command[str]: ...
def _aggregate_keywords(*, kwargs: dict, sep: str, prefix: str): ...

# ---------------------------------------------------------------------------
# contrib — namespace of pre-baked command wrappers
# ---------------------------------------------------------------------------

class contrib:
    git: Command[str]
    bash: Command[str]
    sudo: Command[str]
    ssh: Command[str]

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
