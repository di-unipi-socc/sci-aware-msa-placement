from swiplserver import (
    is_prolog_functor,
    prolog_name,
    prolog_args,
    is_prolog_list,
    is_prolog_atom,
)
from pathlib import Path


def parse_prolog(query):
    if is_prolog_functor(query):
        if prolog_name(query) != ",":
            ans = (prolog_name(query), parse_prolog(prolog_args(query)))
        else:
            ans = tuple(parse_prolog(prolog_args(query)))
    elif is_prolog_list(query):
        ans = [parse_prolog(v) for v in query]
    elif is_prolog_atom(query):
        ans = query
    elif isinstance(query, dict):
        ans = {k: parse_prolog(v) for k, v in query.items()}
    else:
        ans = query
    return ans


def application_path(app_dir: Path, app_name: str) -> Path:
    return app_dir / f"{app_name.lower()}" / "applicationFULLms.pl"
