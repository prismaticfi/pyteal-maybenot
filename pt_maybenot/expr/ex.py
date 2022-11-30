import typing
from abc import ABC
from dataclasses import dataclass, field

import pyteal as pt

if typing.TYPE_CHECKING:
    from pyteal.compiler import CompileOptions


class _AppGetter(pt.Expr, ABC):
    """
    Get state of an external application.

    Used over PyTeal MaybeValue implementation because this wastes a lot of operations on storing
    and loading into ScratchVars, even when branching is not required. This implementation just
    asserts or pops the first value directly (denoting existence of the field) and then leaves the
    resulting value on the stack, or alternatively retrives the existence flag alone (while
    optionally storing the value).
    """

    op: pt.Op

    def __init__(
        self,
        assert_has_value: bool = True,
        get_exists: bool = False,
        slot: pt.ScratchSlot | None = None,
        *args: pt.Expr,
    ):
        super().__init__()

        if assert_has_value and get_exists:
            raise ValueError("Cannot assert and return exists flag simultaneously")
        elif (not get_exists) and slot:
            raise ValueError("Cannot store value in ScratchSlot unless getting exists flag")

        self._slot = slot
        self._args = args
        self._assert_has_value = assert_has_value
        self._get_exists = get_exists

    def __teal__(self, options: "CompileOptions"):
        # push [value, value_exists] on the stack
        get_app_state = pt.TealOp(self, self.op)
        get_start, get_end = pt.TealSimpleBlock.FromOp(options, get_app_state, *self._args)
        # need to swap if returning exists flag
        if self._get_exists:
            swap = pt.TealSimpleBlock(
                [
                    pt.TealOp(self, pt.Op.swap),
                    # if opting not to store, the value simply gets popped
                    pt.TealOp(self, pt.Op.store, self._slot) if self._slot else pt.TealOp(self, pt.Op.pop),
                ]
            )
            get_end.setNextBlock(swap)
            return get_start, swap
        # we assert that the value_exists (1 if exists, 0 if not), or simply pop it if assert_has_value is false
        value_exists_op = pt.Op.assert_ if self._assert_has_value else pt.Op.pop
        value_start, value_end = pt.TealSimpleBlock.FromOp(options, pt.TealOp(self, value_exists_op))
        get_end.setNextBlock(value_start)
        return get_start, value_end

    def __str__(self):
        return f"({self.__class__.__name__} (assert={self._assert_has_value},get_exists={self._get_exists},slot={None if not self._slot else self._slot.id}))"

    def type_of(self):
        if self._get_exists:
            return pt.TealType.uint64
        return pt.TealType.anytype

    def has_return(self) -> bool:
        return False


class _GetExAppLocal(_AppGetter):
    """Get local state from external application."""

    op: pt.Op = pt.Op.app_local_get_ex

    def __init__(
        self,
        account: pt.Expr,
        app: pt.Expr,
        key: pt.Expr,
        assert_has_value: bool = True,
        get_exists: bool = False,
        slot: pt.ScratchSlot | None = None,
    ):
        super().__init__(assert_has_value, get_exists, slot, account, app, key)


class _GetExAppGlobal(_AppGetter):
    """Get global state from external application."""

    op: pt.Op = pt.Op.app_global_get_ex

    def __init__(
        self,
        app: pt.Expr,
        key: pt.Expr,
        assert_has_value: bool = True,
        get_exists: bool = False,
        slot: pt.ScratchSlot | None = None,
    ):
        super().__init__(assert_has_value, get_exists, slot, app, key)


@dataclass(frozen=True, slots=True)
class ExAppLocal:
    account: pt.Expr
    app: pt.Expr
    key: pt.Expr
    type: pt.TealType = pt.TealType.anytype
    scratch: pt.ScratchVar | None = field(default=None, init=False, compare=False)

    def get(self, assert_has_value: bool = True, load: bool = True) -> pt.Expr:
        """
        Get the local state value while optionally asserting that the value exists.

        If the value does not exist and is not asserted, an integer value of 0 is returned.

        If the existence check has already been performed with store enabled, the assert will be
        skipped and the value will be returned directly unless load is explicitly disabled.
        """
        if load and self.scratch:
            return self.scratch.load()
        return _GetExAppLocal(self.account, self.app, self.key, assert_has_value)

    def exists(self, store: bool = True) -> pt.Expr:
        """
        Get the existence flag of the local state value. Returns an integer of 1 if the value exists
        and 0 otherwise.

        If store is enabled, the value will be stored in an available scratch slot.
        """
        if store:
            if not (scratch := self.scratch):
                # reserve new Scratch slot and store value instead of pop
                scratch = pt.ScratchVar(self.type)
                object.__setattr__(self, "scratch", scratch)
            return _GetExAppLocal(
                self.account, self.app, self.key, assert_has_value=False, get_exists=True, slot=scratch.slot
            )
        return _GetExAppLocal(self.account, self.app, self.key, assert_has_value=False, get_exists=True)


@dataclass(frozen=True, slots=True)
class ExAppGlobal:
    app: pt.Expr
    key: pt.Expr
    type: pt.TealType = pt.TealType.anytype
    scratch: pt.ScratchVar | None = field(default=None, init=False, compare=False)

    def get(self, assert_has_value: bool = True, load: bool = True) -> pt.Expr:
        """
        Get the global state value while optionally asserting that the value exists.

        If the value does not exist and is not asserted, an integer value of 0 is returned.

        If the existence check has already been performed with store enabled, the assert will be
        skipped and the cached value will be returned directly unless load is explicitly disabled.
        """
        if load and self.scratch:
            return self.scratch.load()
        return _GetExAppGlobal(self.app, self.key, assert_has_value)

    def exists(self, store: bool = True) -> pt.Expr:
        """
        Get the existence flag of the global state value. Returns an integer of 1 if the value
        exists and 0 otherwise.

        If store is enabled, the value will be cached in an available scratch slot.
        """
        if store:
            if not (scratch := self.scratch):
                # reserve new Scratch slot and store value instead of pop
                scratch = pt.ScratchVar(self.type)
                object.__setattr__(self, "scratch", scratch)
            return _GetExAppGlobal(self.app, self.key, assert_has_value=False, get_exists=True, slot=scratch.slot)
        return _GetExAppGlobal(self.app, self.key, assert_has_value=False, get_exists=True)
