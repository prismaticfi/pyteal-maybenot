import typing
from abc import ABC
from dataclasses import dataclass
from dataclasses import field as field_

import pyteal as pt

if typing.TYPE_CHECKING:
    from pyteal.compiler import CompileOptions


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    teal_type: pt.TealType


# https://developer.algorand.org/docs/get-details/dapps/avm/teal/opcodes/#asset_holding_get-f
AssetHoldingField = typing.Literal["balance", "frozen"]
_ASSET_HOLDING_MAP: dict[AssetHoldingField, Field] = {
    "balance": Field("AssetBalance", pt.TealType.uint64),
    "frozen": Field("AssetFrozen", pt.TealType.uint64),
}

# https://developer.algorand.org/docs/get-details/dapps/avm/teal/opcodes/#asset_params_get-f
AssetParamsField = typing.Literal[
    "total",
    "decimals",
    "default_frozen",
    "unit_name",
    "name",
    "url",
    "metadata_hash",
    "manager",
    "reserve",
    "freeze",
    "clawback",
    "creator",
]
_ASSET_PARAMS_MAP: dict[AssetParamsField, Field] = {
    "total": Field("AssetTotal", pt.TealType.uint64),
    "decimals": Field("AssetDecimals", pt.TealType.uint64),
    "default_frozen": Field("AssetDefaultFrozen", pt.TealType.uint64),
    "unit_name": Field("AssetUnitName", pt.TealType.bytes),
    "name": Field("AssetName", pt.TealType.bytes),
    "url": Field("AssetURL", pt.TealType.bytes),
    "metadata_hash": Field("AssetMetadataHash", pt.TealType.bytes),
    "manager": Field("AssetManager", pt.TealType.bytes),
    "reserve": Field("AssetReserve", pt.TealType.bytes),
    "freeze": Field("AssetFreeze", pt.TealType.bytes),
    "clawback": Field("AssetClawback", pt.TealType.bytes),
    "creator": Field("AssetCreator", pt.TealType.bytes),
}


# https://developer.algorand.org/docs/get-details/dapps/avm/teal/opcodes/#app_params_get-f
AppParamsField = typing.Literal[
    "approval_program",
    "clear_state_program",
    "global_num_uint",
    "global_num_byte_slice",
    "local_num_uint",
    "local_num_byte_slice",
    "extra_program_pages",
    "creator",
    "address",
]
_APP_PARAMS_MAP: dict[AppParamsField, Field] = {
    "approval_program": Field("AppApprovalProgram", pt.TealType.bytes),
    "clear_state_program": Field("AppClearStateProgram", pt.TealType.bytes),
    "global_num_uint": Field("AppGlobalNumUint", pt.TealType.uint64),
    "global_num_byte_slice": Field("AppGlobalNumByteSlice", pt.TealType.uint64),
    "local_num_uint": Field("AppLocalNumUint", pt.TealType.uint64),
    "local_num_byte_slice": Field("AppLocalNumByteSlice", pt.TealType.uint64),
    "extra_program_pages": Field("AppExtraProgramPages", pt.TealType.uint64),
    "creator": Field("AppCreator", pt.TealType.bytes),
    "address": Field("AppAddress", pt.TealType.bytes),
}

# https://developer.algorand.org/docs/get-details/dapps/avm/teal/opcodes/#acct_params_get-f
AcctParamsField = typing.Literal[
    "balance",
    "min_balance",
    "auth_addr",
]
_ACCT_PARAMS_MAP: dict[AcctParamsField, Field] = {
    "balance": Field("AcctBalance", pt.TealType.uint64),
    "min_balance": Field("AcctMinBalance", pt.TealType.uint64),
    "auth_addr": Field("AcctAuthAddr", pt.TealType.bytes),
}


class _FieldGetter(pt.Expr, ABC):
    """
    Get external parameter (asset_holding, asset_params, app_params, acct_params).

    Used over PyTeal MaybeValue implementation because this wastes a lot of operations on storing
    and loading into ScratchVars, even when branching is not required. This implementation just
    asserts or pops the first value directly (denoting existence of the field) and then leaves the
    resulting value on the stack, or alternatively retrives the existence flag alone (while
    optionally storing the value).
    """

    op: pt.Op
    fields: dict[str, Field]

    def __init__(
        self,
        field: str,
        assert_exists: bool = True,
        get_exists: bool = False,
        slot: pt.ScratchSlot | None = None,
        *args: pt.Expr,
    ):
        super().__init__()

        if field not in self.fields:
            raise ValueError(f"{field} not a valid field in {self.__class__.__name__}")

        if assert_exists and get_exists:
            raise ValueError("Cannot assert and return exists flag simultaneously")
        elif (not get_exists) and slot:
            raise ValueError("Cannot store value in ScratchSlot unless getting exists flag")

        self._slot = slot
        self._args = args
        self._field = field
        self._assert_exists = assert_exists
        self._get_exists = get_exists

    def __teal__(self, options: "CompileOptions"):
        # push [value, value_exists] on the stack
        get_field = pt.TealOp(self, self.op, self.fields[self._field].name)
        get_start, get_end = pt.TealSimpleBlock.FromOp(options, get_field, *self._args)
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
        # if assert has value, we assert the value_exists (1 if exists, 0 if not), else just pop it
        value_exists_op = pt.Op.assert_ if self._assert_exists else pt.Op.pop
        value_start, value_end = pt.TealSimpleBlock.FromOp(options, pt.TealOp(self, value_exists_op))
        get_end.setNextBlock(value_start)
        return get_start, value_end

    def __str__(self):
        return f"({self.__class__.__name__} ({self._field},assert={self._assert_exists},get_exists={self._get_exists},slot={None if not self._slot else self._slot.id}))"

    def type_of(self):
        if self._get_exists:
            return pt.TealType.uint64
        return self.fields[self._field].teal_type

    def has_return(self) -> bool:
        return False


class _GetAssetHolding(_FieldGetter):
    """Get asset holding fields."""

    op: pt.Op = pt.Op.asset_holding_get
    fields: dict[AssetHoldingField, Field] = _ASSET_HOLDING_MAP

    def __init__(
        self,
        account: pt.Expr,
        asset: pt.Expr,
        field: AssetHoldingField,
        assert_exists: bool = True,
        get_exists: bool = False,
        slot: pt.ScratchSlot | None = None,
    ):
        super().__init__(field, assert_exists, get_exists, slot, account, asset)


class _GetAssetParams(_FieldGetter):
    """Get asset params fields."""

    op: pt.Op = pt.Op.asset_params_get
    fields: dict[AssetParamsField, Field] = _ASSET_PARAMS_MAP

    def __init__(
        self,
        asset: pt.Expr,
        field: AssetParamsField,
        assert_exists: bool = True,
        get_exists: bool = False,
        slot: pt.ScratchSlot | None = None,
    ):
        super().__init__(field, assert_exists, get_exists, slot, asset)


class _GetAppParams(_FieldGetter):
    """Get app params fields."""

    op: pt.Op = pt.Op.app_params_get
    fields: dict[AppParamsField, Field] = _APP_PARAMS_MAP

    def __init__(
        self,
        app: pt.Expr,
        field: AppParamsField,
        assert_exists: bool = True,
        get_exists: bool = False,
        slot: pt.ScratchSlot | None = None,
    ):
        super().__init__(field, assert_exists, get_exists, slot, app)


class _GetAcctParams(_FieldGetter):
    """Get app params fields."""

    op: pt.Op = pt.Op.acct_params_get
    fields: dict[AcctParamsField, Field] = _ACCT_PARAMS_MAP

    def __init__(
        self,
        account: pt.Expr,
        field: AcctParamsField,
        assert_exists: bool = True,
        get_exists: bool = False,
        slot: pt.ScratchSlot | None = None,
    ):
        super().__init__(field, assert_exists, get_exists, slot, account)


@dataclass(frozen=True, slots=True)
class AssetHolding:
    account: pt.Expr
    asset: pt.Expr
    field: AssetHoldingField
    scratch: pt.ScratchVar | None = field_(default=None, init=False, compare=False)

    def get(self, assert_exists: bool = True, load: bool = True) -> pt.Expr:
        """
        Get the asset holding value while optionally asserting that the value exists.

        If the value does not exist and is not asserted, an integer value of 0 is returned.

        If the existence check has already been performed with store enabled, the assert will be
        skipped and the value will be returned directly unless load is explicitly disabled.
        """
        if load and self.scratch:
            return self.scratch.load()
        return _GetAssetHolding(self.account, self.asset, self.field, assert_exists)

    def exists(self, store: bool = True) -> pt.Expr:
        """
        Get the existence flag of the asset holding value. Returns an integer of 1 if the value
        exists and 0 otherwise.

        If store is enabled, the value will be stored in an available scratch slot.
        """
        if store:
            if not (scratch := self.scratch):
                # reserve new Scratch slot and store value instead of pop
                scratch = pt.ScratchVar(_ASSET_HOLDING_MAP[self.field].teal_type)
                object.__setattr__(self, "scratch", scratch)
            return _GetAssetHolding(
                self.account, self.asset, self.field, assert_exists=False, get_exists=True, slot=scratch.slot
            )
        return _GetAssetHolding(self.account, self.asset, self.field, assert_exists=False, get_exists=True)


@dataclass(frozen=True, slots=True)
class AssetParams:
    asset: pt.Expr
    field: AssetParamsField
    scratch: pt.ScratchVar | None = field_(default=None, init=False, compare=False)

    def get(self, assert_exists: bool = True, load: bool = True) -> pt.Expr:
        """
        Get the asset params value while optionally asserting that the value exists.

        If the value does not exist and is not asserted, an integer value of 0 is returned.

        If the existence check has already been performed with store enabled, the assert will be
        skipped and the value will be returned directly unless load is explicitly disabled.
        """
        if load and self.scratch:
            return self.scratch.load()
        return _GetAssetParams(self.asset, self.field, assert_exists)

    def exists(self, store: bool = True) -> pt.Expr:
        """
        Get the existence flag of the asset params value. Returns an integer of 1 if the value
        exists and 0 otherwise.

        If store is enabled, the value will be stored in an available scratch slot.
        """
        if store:
            if not (scratch := self.scratch):
                # reserve new Scratch slot and store value instead of pop
                scratch = pt.ScratchVar(_ASSET_PARAMS_MAP[self.field].teal_type)
                object.__setattr__(self, "scratch", scratch)
            return _GetAssetParams(self.asset, self.field, assert_exists=False, get_exists=True, slot=scratch.slot)
        return _GetAssetParams(self.asset, self.field, assert_exists=False, get_exists=True)


@dataclass(frozen=True, slots=True)
class AppParams:
    app: pt.Expr
    field: AppParamsField
    scratch: pt.ScratchVar | None = field_(default=None, init=False, compare=False)

    def get(self, assert_exists: bool = True, load: bool = True) -> pt.Expr:
        """
        Get the app params value while optionally asserting that the value exists.

        If the value does not exist and is not asserted, an integer value of 0 is returned.

        If the existence check has already been performed with store enabled, the assert will be
        skipped and the value will be returned directly unless load is explicitly disabled.
        """
        if load and self.scratch:
            return self.scratch.load()
        return _GetAppParams(self.app, self.field, assert_exists)

    def exists(self, store: bool = True) -> pt.Expr:
        """
        Get the existence flag of the app params value. Returns an integer of 1 if the value exists
        and 0 otherwise.

        If store is enabled, the value will be stored in an available scratch slot.
        """
        if store:
            if not (scratch := self.scratch):
                # reserve new Scratch slot and store value instead of pop
                scratch = pt.ScratchVar(_APP_PARAMS_MAP[self.field].teal_type)
                object.__setattr__(self, "scratch", scratch)
            return _GetAppParams(self.app, self.field, assert_exists=False, get_exists=True, slot=scratch.slot)
        return _GetAppParams(self.app, self.field, assert_exists=False, get_exists=True)


@dataclass(frozen=True, slots=True)
class AcctParams:
    account: pt.Expr
    field: AcctParamsField
    scratch: pt.ScratchVar | None = field_(default=None, init=False, compare=False)

    def get(self, assert_exists: bool = True, load: bool = True) -> pt.Expr:
        """
        Get the account params value while optionally asserting that the value exists.

        If the value does not exist and is not asserted, an integer value of 0 is returned.

        If the existence check has already been performed with store enabled, the assert will be
        skipped and the value will be returned directly unless load is explicitly disabled.
        """
        if load and self.scratch:
            return self.scratch.load()
        return _GetAcctParams(self.account, self.field, assert_exists)

    def exists(self, store: bool = True) -> pt.Expr:
        """
        Get the existence flag of the account params value. Returns an integer of 1 if the value
        exists and 0 otherwise.

        If store is enabled, the value will be stored in an available scratch slot.
        """
        if store:
            if not (scratch := self.scratch):
                # reserve new Scratch slot and store value instead of pop
                scratch = pt.ScratchVar(_ACCT_PARAMS_MAP[self.field].teal_type)
                object.__setattr__(self, "scratch", scratch)
            return _GetAcctParams(self.account, self.field, assert_exists=False, get_exists=True, slot=scratch.slot)
        return _GetAcctParams(self.account, self.field, assert_exists=False, get_exists=True)
