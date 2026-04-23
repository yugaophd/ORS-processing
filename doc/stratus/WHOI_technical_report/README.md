# Stratus Ocean Reference Station Technical Report

## Overview

This directory contains the comprehensive WHOI Technical Report for the Stratus Ocean Reference Station deep ocean temperature and salinity data, covering deployments 12-22 (2012-2025).

## Document Structure

### Main Document
- **`stratus_technical_report.tex`**: Master LaTeX file that compiles all chapters into a single unified technical report
- **`stratus_technical_report.pdf`**: The compiled PDF (183 pages, 4.3 MB)

### Individual Deployment Chapters
Each deployment (12-22) has its own subdirectory containing:
- `stratusXX_data_report.tex`: The original standalone report
- `stratusXX_chapter.tex`: Chapter-formatted version (extracted body content for inclusion in the master report)
- `spike_stats.tex`: Statistical tables for spike removal
- `diff_stats.tex`: Sensor difference statistics tables
- `deployment_distance.tex`: (for some deployments) Information about deployment overlaps
- Supporting PNG files: Figures for overlap analysis and merge points

## Formatting

The technical report follows WHOI standard formatting guidelines:
- **Font**: Times New Roman, 12pt
- **Margins**: 1 inch on all sides
- **Line spacing**: 1.5 (one-and-a-half spacing)
- **Document class**: Report (with chapters)
- **Paper size**: US Letter (8.5" × 11")

## Compilation Instructions

### Basic Compilation
To compile the complete technical report:

```bash
cd /Users/yugao/UOP/ORS-processing/doc/stratus/WHOI_technical_report
pdflatex stratus_technical_report.tex
pdflatex stratus_technical_report.tex  # Run twice for cross-references
```

### Alternative: Using the provided compile line
```bash
pdflatex -interaction=nonstopmode stratus_technical_report.tex
```

### Individual Deployment Reports
Each deployment can also be compiled as a standalone report:
```bash
cd XX/  # where XX is the deployment number (12-22)
pdflatex stratusXX_data_report.tex
```

## Content Organization

### Front Matter
1. Title page
2. Abstract
3. Table of contents
4. List of figures
5. List of tables

### Main Content
- **Chapter 1**: Stratus 12 (2012-2014)
- **Chapter 2**: Stratus 13 (2014-2015)
- **Chapter 3**: Stratus 14 (2015-2016)
- **Chapter 4**: Stratus 15 (2016-2017)
- **Chapter 5**: Stratus 16 (2017-2018)
- **Chapter 6**: Stratus 17 (2018-2019)
- **Chapter 7**: Stratus 18 (2019-2020)
- **Chapter 8**: Stratus 19 (2020-2021)
- **Chapter 9**: Stratus 20 (2021-2022)
- **Chapter 10**: Stratus 21 (2022-2023)
- **Chapter 11**: Stratus 22 (2023-2025)

Each chapter follows a consistent structure:
1. Introduction and Deployment Summary
2. Pre-Processing (data loading, time correction)
3. Truncation and Visualization
4. Quality Control and Deployment Catalog
5. Documentation and Archiving
6. Conclusion

## Image Dependencies

The report references images from:
```
/Users/yugao/UOP/ORS-processing/img/
```

Ensure this directory exists and contains all required figures before compilation.

## Technical Details

### Packages Used
- `geometry`: Page layout
- `graphicx`: Figure inclusion
- `amsmath`: Mathematical typesetting
- `hyperref`: Hyperlinks and PDF bookmarks
- `xcolor`: Color support
- `float`: Float positioning (figures/tables)
- `ifthen`: Conditional logic
- `times`: Times font family
- `setspace`: Line spacing control
- `booktabs`: Professional-quality tables
- `longtable`: Multi-page tables

### Known Issues
- Some warnings about multiply-defined labels (due to similar figure/table references across chapters)
- Some undefined control sequences for deployment-specific variables that vary between chapters
- These warnings do not affect the final PDF output quality

## Maintenance

### Adding a New Deployment
1. Create new subdirectory for the deployment (e.g., `23/`)
2. Place the standalone report as `stratus23_data_report.tex`
3. Run the extraction script to create `stratus23_chapter.tex`
4. Add the chapter to `stratus_technical_report.tex`:
   ```latex
   \chapter{Stratus 23 (YYYY-YYYY)}
   \input{23/stratus23_chapter}
   ```
5. Recompile the master document

### Updating Existing Chapters
1. Edit the standalone report in the deployment subdirectory
2. Re-run the extraction script to update the chapter file
3. Recompile the master document

## Author
Yu Gao  
Upper Ocean Processes Group  
Woods Hole Oceanographic Institution  
Woods Hole, MA 02543  
yugao@whoi.edu

## Date
Generated: November 2025

## Version History
- v1.0 (November 2025): Initial compilation of deployments 12-22
