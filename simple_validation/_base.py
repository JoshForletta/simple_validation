from io import StringIO
from typing import Any


class FailedValidation(Exception):
    pass


def _format_failed_validations(fvs: list[tuple[str, str, FailedValidation]]) -> str:
    print(fvs)
    rs = StringIO()
    for vn, value, e in fvs:
        rs.write("\n\t{}({}):\n\t\t".format(vn, value))
        rs.write("\n\t\t".join(
            ("\t\t".join(str(a).splitlines(keepends=True)) for a in e.args) 
        ))

    rs.seek(0); return rs.read()