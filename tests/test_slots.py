import itertools

import pyteal as pt

import pt_maybenot as ptmn

from .utils import compile, format_teal


def test_slots_on_cache():
    # test that scratch slot allocation in remaining program accounts for value cache
    for i in range(3):
        for j in range(3):
            balance = ptmn.AssetHolding(pt.Txn.sender(), pt.Txn.assets[0], "balance")
            # declare scratch vars before and after store
            pre_scratch = [pt.ScratchVar() for _ in range(i)]
            post_scratch = [pt.ScratchVar() for _ in range(j)]
            teal = compile(
                *[s.store(pt.Int(n)) for n, s in enumerate(pre_scratch)],
                pt.Pop(balance.exists()),
                *[s.store(pt.Int(i + n)) for n, s in enumerate(post_scratch)],
                pt.Int(1),
            )
            # generate TEAL for scratch allocations before- and after balance store
            pre_teal = [f"int {n}\nstore {n}" for n in range(i)]
            store_teal = [
                "txn Sender",
                "txna Assets 0",
                "asset_holding_get AssetBalance",
                "swap",
                # the balance store is reserved last - no stores before / after overlap with slot i+j
                f"store {i+j}",
                "pop",
            ]
            post_teal = [f"int {i + n}\nstore {i + n}" for n in range(j)]
            ptt = "\n".join(itertools.chain(pre_teal, store_teal, post_teal, ["int 1", "return"]))
            assert teal == format_teal(ptt, trim=False)


def test_slots_without_cache():
    # test that scratch slot allocation in remaining program is unaffected if not caching value
    for i in range(3):
        for j in range(3):
            balance = ptmn.AssetHolding(pt.Txn.sender(), pt.Txn.assets[0], "balance")
            # declare scratch vars before and after store
            pre_scratch = [pt.ScratchVar() for _ in range(i)]
            post_scratch = [pt.ScratchVar() for _ in range(j)]
            teal = compile(
                *[s.store(pt.Int(n)) for n, s in enumerate(pre_scratch)],
                pt.Pop(balance.exists(store=False)),
                # post-store enumeration is unaffected since balance store was last slot
                *[s.store(pt.Int(i + n)) for n, s in enumerate(post_scratch)],
                pt.Int(1),
            )
            # generate TEAL for scratch allocations before- and after balance store
            pre_teal = [f"int {n}\nstore {n}" for n in range(i)]
            store_teal = [
                "txn Sender",
                "txna Assets 0",
                "asset_holding_get AssetBalance",
                "swap",
                # popping value replaces store
                "pop",
                "pop",
            ]
            post_teal = [f"int {i + n}\nstore {i + n}" for n in range(j)]
            ptt = "\n".join(itertools.chain(pre_teal, store_teal, post_teal, ["int 1", "return"]))
            assert teal == format_teal(ptt, trim=False)
