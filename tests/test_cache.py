import pyteal as pt

import pt_maybenot as ptmn

from .utils import compile, compile_popped, format_teal

JUMP_TO_GET_BRANCH_IF_TRUE = "bnz main_l2"
GET_BRANCH = "main_l2:"


def test_cache_asset_holding():
    balance = ptmn.AssetHolding(pt.Txn.sender(), pt.Txn.assets[0], "balance")
    teal = compile(pt.If(balance.exists(), balance.get(), pt.Int(0)))
    assert teal == format_teal(
        f"""
        txn Sender
        txna Assets 0
        asset_holding_get AssetBalance
        swap
        store 0
        {JUMP_TO_GET_BRANCH_IF_TRUE}
        int 0
        b main_l3
        {GET_BRANCH}
        load 0
        main_l3:
        return
        """
    )


def test_cache_asset_params():
    name = ptmn.AssetParams(pt.Txn.assets[0], "name")
    # pop since program cannot return bytes
    teal = compile_popped(pt.If(name.exists(), name.get(), pt.Bytes("none")))
    assert teal == format_teal(
        f"""
        txna Assets 0
        asset_params_get AssetName
        swap
        store 0
        {JUMP_TO_GET_BRANCH_IF_TRUE}
        byte \"none\"
        b main_l3
        {GET_BRANCH}
        load 0
        main_l3:
        pop
        int 1
        return
        """
    )


def test_cache_app_params():
    local_num_uint = ptmn.AppParams(pt.Txn.applications[1], "local_num_uint")
    teal = compile(pt.If(local_num_uint.exists(), local_num_uint.get(), pt.Int(0)))
    assert teal == format_teal(
        f"""
        txna Applications 1
        app_params_get AppLocalNumUint
        swap
        store 0
        {JUMP_TO_GET_BRANCH_IF_TRUE}
        int 0
        b main_l3
        {GET_BRANCH}
        load 0
        main_l3:
        return
        """
    )


def test_cache_acct_params():
    auth_addr = ptmn.AcctParams(pt.Txn.sender(), "auth_addr")
    teal = compile_popped(pt.If(auth_addr.exists(), auth_addr.get(), pt.Bytes("none")))
    assert teal == format_teal(
        f"""
        txn Sender
        acct_params_get AcctAuthAddr
        swap
        store 0
        {JUMP_TO_GET_BRANCH_IF_TRUE}
        byte \"none\"
        b main_l3
        {GET_BRANCH}
        load 0
        main_l3:
        pop
        int 1
        return
        """
    )


def test_cache_local():
    key = ptmn.ExAppLocal(pt.Txn.sender(), pt.Txn.applications[1], pt.Bytes("key"))
    teal = compile_popped(pt.If(key.exists(), key.get(), pt.Bytes("none")))
    assert teal == format_teal(
        f"""
        txn Sender
        txna Applications 1
        byte \"key\"
        app_local_get_ex
        swap
        store 0
        {JUMP_TO_GET_BRANCH_IF_TRUE}
        byte \"none\"
        b main_l3
        {GET_BRANCH}
        load 0
        main_l3:
        pop
        int 1
        return
        """
    )


def test_cache_global():
    # pop not needed since app state is any-typed
    key = ptmn.ExAppGlobal(pt.Txn.applications[1], pt.Bytes("key"))
    teal = compile(pt.If(key.exists(), key.get(), pt.Int(0)))
    assert teal == format_teal(
        f"""
        txna Applications 1
        byte \"key\"
        app_global_get_ex
        swap
        store 0
        {JUMP_TO_GET_BRANCH_IF_TRUE}
        int 0
        b main_l3
        {GET_BRANCH}
        load 0
        main_l3:
        return
        """
    )


def test_no_cache_on_inline():
    # test that no caching happens if inlining - but still produces correct code
    teal = compile(
        pt.If(
            ptmn.AssetHolding(pt.Txn.sender(), pt.Txn.assets[0], "balance").exists(),
            ptmn.AssetHolding(pt.Txn.sender(), pt.Txn.assets[0], "balance").get(),
            pt.Int(0),
        )
    )
    assert teal == format_teal(
        f"""
        txn Sender
        txna Assets 0
        asset_holding_get AssetBalance
        swap
        store 0
        {JUMP_TO_GET_BRANCH_IF_TRUE}
        int 0
        b main_l3
        {GET_BRANCH}
        txn Sender
        txna Assets 0
        asset_holding_get AssetBalance
        assert
        main_l3:
        return
        """
    )
