import pyteal as pt

import pt_maybenot as ptmn

from .utils import compile, format_teal

JUMP_TO_GET_BRANCH_IF_TRUE = "bnz main_l2"
GET_BRANCH = "main_l2:"


def test_no_cache_on_exists_override():
    # test that no caching happens when explicitly disabling store on exists check
    key = ptmn.ExAppGlobal(pt.Txn.applications[1], pt.Bytes("key"))
    teal = compile(pt.If(key.exists(store=False), key.get(), pt.Int(0)))
    assert teal == format_teal(
        f"""
        txna Applications 1
        byte \"key\"
        app_global_get_ex
        swap
        pop
        {JUMP_TO_GET_BRANCH_IF_TRUE}
        int 0
        b main_l3
        {GET_BRANCH}
        txna Applications 1
        byte \"key\"
        app_global_get_ex
        assert
        main_l3:
        return
        """
    )


def test_no_cache_on_get_override():
    # test that no caching happens when explicitly disabling loading on getter
    key = ptmn.ExAppGlobal(pt.Txn.applications[1], pt.Bytes("key"))
    teal = compile(pt.If(key.exists(), key.get(load=False), pt.Int(0)))
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
        txna Applications 1
        byte \"key\"
        app_global_get_ex
        assert
        main_l3:
        return
        """
    )
