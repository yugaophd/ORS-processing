"""Verify all \\includegraphics references in chapter .tex files resolve to
files that exist on disk. Substitutes the per-chapter macros for projectname,
casenumber, FirstInstrument, SecondInstrument, previouscasenumber, imagepath.
"""
from __future__ import annotations
import re
from pathlib import Path

REPORT = {
    "stratus": Path("/Users/yugao/UOP/ORS-processing/doc/stratus/WHOI_technical_report"),
    "ntas": Path("/Users/yugao/UOP/ORS-processing/doc/NTAS/WHOI_technical_report"),
}
IMG_BASE = {
    "stratus": Path("/Users/yugao/UOP/ORS-processing/img/STRATUS"),
    "ntas": Path("/Users/yugao/UOP/ORS-processing/img/NTAS"),
}
DEPS = {"stratus": list(range(12, 23)), "ntas": list(range(11, 21))}


def read_macros(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for m in re.finditer(r"\\(?:re)?newcommand\{\\([A-Za-z]+)\}(?:\[\d+\])?\{([^}]*)\}", path.read_text()):
        out[m.group(1)] = m.group(2)
    return out


def expand(s: str, macros: dict[str, str]) -> str:
    prev = None
    while prev != s:
        prev = s
        for k, v in macros.items():
            s = re.sub(r"\\" + k + r"(?![A-Za-z])", lambda _m, v=v: v, s)
    return s


def main() -> None:
    issues: list[str] = []
    for project, rdir in REPORT.items():
        for dep in DEPS[project]:
            chap_dir = rdir / f"{dep}"
            if not chap_dir.exists():
                continue
            macros = read_macros(chap_dir / "macros.tex")
            # default imagepath relative to chapter
            macros.setdefault("imagepath", f"../../../../img/{'STRATUS' if project=='stratus' else 'NTAS'}")
            for tex in chap_dir.glob("*.tex"):
                text = tex.read_text()
                # collect inline newcommands in the chapter file too
                local = dict(macros)
                for m in re.finditer(r"\\(?:re)?newcommand\{\\([A-Za-z]+)\}(?:\[\d+\])?\{([^}]*)\}", text):
                    local[m.group(1)] = m.group(2)
                for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
                    # Skip if this \includegraphics sits inside an \IfFileExists guard
                    start = m.start()
                    # Look back at most 400 chars for an unmatched \IfFileExists{...}{
                    snippet = text[max(0, start - 600):start]
                    if snippet.count("\\IfFileExists{") > 0:
                        last_if = snippet.rfind("\\IfFileExists{")
                        # crude check: if between last_if and start there are at least two `{`, treat as inside guard
                        between = snippet[last_if:]
                        if between.count("{") - between.count("}") >= 1:
                            continue
                    ref = expand(m.group(1), local)
                    if "\\" in ref or "{" in ref:
                        issues.append(f"[{project} {dep} {tex.name}] unresolved macro: {ref}")
                        continue
                    # imagepath in chapter macros is "../img/STRATUS" relative to chapter root build
                    # actual resolution: chap_dir/ref
                    p = (chap_dir / ref).resolve()
                    # also try img base directly (graphicspath)
                    if not p.exists():
                        graphicspath = Path("/Users/yugao/UOP/ORS-processing/img")
                        candidates = [
                            graphicspath / ref,
                            graphicspath / Path(ref).name,
                            IMG_BASE[project] / Path(ref).name,
                        ]
                        if "deployment_maps" in ref:
                            candidates.append(Path("/Users/yugao/UOP/ORS-processing/img/deployment_maps") / Path(ref).name)
                        if any(c.exists() for c in candidates):
                            continue
                        issues.append(f"[{project} {dep} {tex.name}] missing figure: {ref}")
    for i in issues:
        print(i)
    if not issues:
        print("All figures resolve.")


if __name__ == "__main__":
    main()
