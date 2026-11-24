# hackViz – UCS503 End-Semester Report (LaTeX)

LaTeX source of the end-semester project report (Group 3C25).

| Path | Contents |
|---|---|
| `main.tex` | The report |
| `tietreport.cls` | TIET report class used by `main.tex` |
| `figures/` | Diagrams (use case, activity, swimlane, DFD levels 0–2, class, sequence) and screenshots |
| `diagrams_src/` | Python/Node scripts that generate the diagrams (`simple_diagrams.py` draws the ones used in the report) |
| `presentation/` | Script that builds the 10-slide presentation from the same figures |

## Build the PDF

Run `pdflatex` twice from this folder (the second run fills in the table of contents and references):

```bash
pdflatex main.tex
pdflatex main.tex
```

Works with MiKTeX, TeX Live or Overleaf (upload `main.tex`, `tietreport.cls` and the `figures/` folder).

## Regenerate the diagrams (optional)

```bash
cd diagrams_src
npm install                     # puppeteer-core, uses the installed Google Chrome
python simple_diagrams.py svg
node render_diagrams.mjs svg ../figures
node to_jpeg.mjs ../figures
```
