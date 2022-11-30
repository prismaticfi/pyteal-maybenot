import textwrap

import pyteal as pt

TEAL_VERSION = 7


def compile(*exprs: pt.Expr):
    return pt.compileTeal(pt.Seq(*exprs), mode=pt.Mode.Application, version=TEAL_VERSION)


def compile_popped(*exprs: pt.Expr):
    # compile popped PyTeal leaving integer 1 on the stack
    return pt.compileTeal(pt.Seq(pt.Pop(pt.Seq(*exprs)), pt.Int(1)), mode=pt.Mode.Application, version=TEAL_VERSION)


def format_teal(teal: str, trim: bool = True):
    # add pragma, align indentation and remove leading- and final linebreak
    start = 1 if trim else None
    stop = -1 if trim else None
    return f"#pragma version {TEAL_VERSION}\n" + textwrap.dedent(teal[start:])[:stop]
