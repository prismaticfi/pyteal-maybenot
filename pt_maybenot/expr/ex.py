import typing
from abc import ABC

import pyteal as pt

if typing.TYPE_CHECKING:
    from pyteal.compiler import CompileOptions


class _AppGetter(pt.Expr, ABC):
    """
    Get state of an external application.

    Used over PyTeal MaybeValue implementation because this wastes a lot of operations on storing
    and loading into ScratchVars. This implementation just asserts or pops the first value directly
    (denoting existence of the field) and then leaves the resulting value on the stack, which can
    then be stored in a ScratchVar manually if needed, or returns the exists flag to branch from.
    """

    op: pt.Op

    def __init__(self, assert_has_value: bool = True, get_exists: bool = False, *args: pt.Expr):
        super().__init__()

        if assert_has_value and get_exists:
            raise ValueError("Cannot assert and return exists flag simultaneously")

        self._args = args
        self._assert_has_value = assert_has_value
        self._get_exists = get_exists

    def __teal__(self, options: "CompileOptions"):
        # push [value, value_exists] on the stack
        get_app_state = pt.TealOp(self, self.op)
        get_start, get_end = pt.TealSimpleBlock.FromOp(options, get_app_state, *self._args)
        # if we're only getting the exists flag, swap and pop the return value => only exists flag remains on the stack
        if self._get_exists:
            swap_and_pop = pt.TealSimpleBlock(
                [
                    pt.TealOp(self, pt.Op.swap),
                    pt.TealOp(self, pt.Op.pop),
                ]
            )
            get_end.setNextBlock(swap_and_pop)
            return get_start, swap_and_pop
        # if assert has value, we assert the value_exists (1 if exists, 0 if not), else just pop it
        value_exists_op = pt.Op.assert_ if self._assert_has_value else pt.Op.pop
        value_start, value_end = pt.TealSimpleBlock.FromOp(options, pt.TealOp(self, value_exists_op))
        get_end.setNextBlock(value_start)
        return get_start, value_end

    def __str__(self):
        return f"({self.__class__.__name__} (assert={self._assert_has_value},get_exists={self._get_exists}))"

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
        self, account: pt.Expr, app: pt.Expr, key: pt.Expr, assert_has_value: bool = True, get_exists: bool = False
    ):
        super().__init__(assert_has_value, get_exists, account, app, key)


class _GetExAppGlobal(_AppGetter):
    """Get global state from external application."""

    op: pt.Op = pt.Op.app_global_get_ex

    def __init__(self, app: pt.Expr, key: pt.Expr, assert_has_value: bool = True, get_exists: bool = False):
        super().__init__(assert_has_value, get_exists, app, key)
