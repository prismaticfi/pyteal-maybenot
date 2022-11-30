import pyteal as pt

import pt_maybenot as ptmn
from pt_maybenot.expr.params import _ACCT_PARAMS_MAP, _APP_PARAMS_MAP, _ASSET_HOLDING_MAP, _ASSET_PARAMS_MAP

from .utils import compile_popped, format_teal


def test_get_asset_holding():
    for field, teal_field in _ASSET_HOLDING_MAP.items():
        # pop to keep return type as int
        teal = compile_popped(ptmn.AssetHolding(pt.Txn.sender(), pt.Txn.assets[0], field).get())
        assert teal == format_teal(
            f"""
            txn Sender
            txna Assets 0
            asset_holding_get {teal_field.name}
            assert
            pop
            int 1
            return
            """
        )


def test_get_asset_params():
    for field, teal_field in _ASSET_PARAMS_MAP.items():
        teal = compile_popped(ptmn.AssetParams(pt.Txn.assets[0], field).get())
        assert teal == format_teal(
            f"""
            txna Assets 0
            asset_params_get {teal_field.name}
            assert
            pop
            int 1
            return
            """
        )


def test_get_app_params():
    for field, teal_field in _APP_PARAMS_MAP.items():
        teal = compile_popped(ptmn.AppParams(pt.Txn.applications[1], field).get())
        assert teal == format_teal(
            f"""
            txna Applications 1
            app_params_get {teal_field.name}
            assert
            pop
            int 1
            return
            """
        )


def test_get_acct_params():
    for field, teal_field in _ACCT_PARAMS_MAP.items():
        teal = compile_popped(ptmn.AcctParams(pt.Txn.sender(), field).get())
        assert teal == format_teal(
            f"""
            txn Sender
            acct_params_get {teal_field.name}
            assert
            pop
            int 1
            return
            """
        )


def test_get_local():
    teal = compile_popped(ptmn.ExAppLocal(pt.Txn.sender(), pt.Txn.applications[1], pt.Bytes("key")).get())
    assert teal == format_teal(
        f"""
        txn Sender
        txna Applications 1
        byte \"key\"
        app_local_get_ex
        assert
        pop
        int 1
        return
        """
    )


def test_get_global():
    teal = compile_popped(ptmn.ExAppGlobal(pt.Txn.applications[1], pt.Bytes("key")).get())
    assert teal == format_teal(
        f"""
        txna Applications 1
        byte \"key\"
        app_global_get_ex
        assert
        pop
        int 1
        return
        """
    )
