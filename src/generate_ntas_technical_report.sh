#!/bin/sh
set -eu

root=/Users/yugao/UOP/ORS-processing/doc/NTAS
out=/Users/yugao/UOP/ORS-processing/doc/NTAS/WHOI_technical_report

for d in 11 12 13 14 15 16 17 18 19 20; do
  src="$root/$d/NTAS${d}_data_report.tex"
  dst="$out/$d"
  body_tmp="$dst/body.tmp"
  macros_tmp="$dst/macros.tmp"

  awk '/\\begin\{document\}/{flag=1; next} /\\end\{document\}/{flag=0} flag {print}' "$src" \
    | sed '/^\\maketitle$/d;/^\\tableofcontents$/d;/^\\newpage$/d' > "$body_tmp"

  perl -0pi -e 's/\\label\{fig:([^}]+)\}/\\label{fig:ntas'"$d"'_\1}/g; s/\\ref\{fig:([^}]+)\}/\\ref{fig:ntas'"$d"'_\1}/g' "$body_tmp"

  awk '/\\begin\{document\}/{exit} /^\\newcommand\{/{print}' "$src" > "$macros_tmp"

  if grep -q '^\\newcommand{\\pressurenote}{}' "$macros_tmp"; then
    printf '%s\n' '\ifthenelse{\equal{\pressureavailable}{no}}{' >> "$macros_tmp"
    printf '%s\n' '    \renewcommand{\pressurenote}{ The pressure data is not available for this deployment, so the pressure variable is not shown in this figure.}' >> "$macros_tmp"
    printf '%s\n' '}{}' >> "$macros_tmp"
  fi

  if [ "$d" = "11" ]; then
    {
      printf '%% Chapter content for NTAS %s - extracted from NTAS%s_data_report.tex\n' "$d" "$d"
      printf '%% This file contains only the body content without preamble or document structure\n\n'
      cat "$macros_tmp"
      printf '\n'
      cat "$body_tmp"
    } > "$dst/ntas${d}_chapter.tex"
  else
    {
      printf '%% Macros for NTAS %s - used by NTAS_technical_report.tex\n' "$d"
      sed 's/^\\newcommand/\\renewcommand/' "$macros_tmp"
    } > "$dst/macros.tex"

    {
      printf '%% Chapter content for NTAS %s - extracted from NTAS%s_data_report.tex\n' "$d" "$d"
      printf '%% This file contains only the body content without preamble or document structure\n\n'
      cat "$body_tmp"
    } > "$dst/ntas${d}_chapter.tex"
  fi

  for aux in spike_stats.tex diff_stats.tex deployment_distance.tex notes.tex; do
    if [ -f "$root/$d/$aux" ]; then
      cp "$root/$d/$aux" "$dst/$aux"
    fi
  done

  rm -f "$body_tmp" "$macros_tmp"
done

echo done
