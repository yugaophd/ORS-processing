# Stratus Technical Report - Reviewer Edits Summary

**Report:** Stratus Ocean Reference Station: Deep-Ocean Temperature and Salinity Data Deployments 12–22 (2012–2025)

**Date Completed:** June 29, 2026

---

## Completed Tasks

### 1. ✅ NOAA Funding Support
- **Location:** `00/introduction_chapter.tex`
- **Change:** Added "and is supported by the NOAA Global Ocean Monitoring and Observing Program."
- **Context:** Acknowledgment of NOAA program support in the project overview

### 2. ✅ Server Name Correction
- **Instances:** 21 replacements across 21 files
- **Change:** report text updated to reference the UOP server
- **Files Modified:**
  - Main chapters: stratus12_chapter.tex through stratus22_chapter.tex (11 files)
  - Data reports: STRATUS12_data_report.tex through stratus22_data_report.tex (11 files)
- **Context:** "recover.xls spreadsheet on the UOP server"

### 3. ✅ Deployment-Specific Sample Interval Wording
- **SBE-16 (Stratus 12-13):** "+/- 5 minutes for the Stratus NN deployment"
- **SBE-37 (Stratus 14-22):** "+/- 30 minutes for the Stratus NN deployment"
- **Total updates:** 33 replacements (22 main chapters + 11 data reports)
- **Also updated:** "differences are consistently within X minutes" text

### 4. ✅ Deployment-Location Plot Markers
- **File:** `src/plot_function.py`
- **Changes:**
  - Converted filled markers to open circles (`marker='o'`, `facecolors='none'`)
  - Ensures overlapping deployment points remain visible
  - Edge colors match colormap for consistency
- **Purpose:** Improve visibility when deployment locations overlap

### 5. ✅ Salinity Calculation Verification
- **Status:** Confirmed using fixed pressure from instrument depth
- **Implementation:** `src/all_stratus_processing.py` (lines 165-220)
  - Uses `gsw.p_from_z()` to calculate pressure from instrument depth
  - Applies TEOS-10 equations with calculated pressure (not measured pressure)
  - Computes both practical and absolute salinity
- **Documentation:** Introduction section clearly states this approach

### 6. ✅ QC Spike Removal Documentation
- **Files Updated:** Stratus 15, 18, 19 deployment chapters
- **Addition:** Explanation of rolling-window spike detector limitations
- **Content Covers:**
  - Large initial transients extending over multiple data points
  - Broad or step-like conductivity/salinity changes
  - Artifacts at time-window edges
- **Recommendation:** Use human-in-the-loop review for undetected issues

---

## Modified Files Summary

| Category | Count | Examples |
|----------|-------|----------|
| Main chapter files | 11 | stratus12_chapter.tex – stratus22_chapter.tex |
| Data report files | 11 | STRATUS12_data_report.tex – stratus22_data_report.tex |
| Introduction file | 1 | 00/introduction_chapter.tex |
| Python code files | 1 | src/plot_function.py |
| **Total** | **24** | — |

---

## Build & Verification Results

✅ **PDF Compilation:** Successful  
✅ **Page Count:** 198 pages  
✅ **File Size:** 57.9 MB  
✅ **LaTeX Errors:** None  
✅ **Cross-references:** All updated  

### Verification Checklist
- ✅ Report text now references the UOP server
- ✅ All "the UOP server" replacements confirmed (21 instances)
- ✅ NOAA support statement present in introduction
- ✅ Deployment-specific sample interval wording applied
- ✅ Deployment-location markers updated to open symbols
- ✅ Salinity uses fixed pressure from instrument depth
- ✅ QC documentation added for affected deployments

---

## Technical Details

### Salinity Calculation Method
The report uses a constant pressure derived from instrument depth for TEOS-10 calculations:
```python
z = -1 * instrument_depth  # negative because depth is positive downward
calculated_pressure = gsw.p_from_z(z, lat)  # Calculate pressure from depth
practical_salinity = gsw.SP_from_C(conductivity, temperature, pressure_values)
absolute_salinity = gsw.SA_from_SP(practical_salinity, pressure_values, lon, lat)
```

### Deployment-Specific Sample Intervals
- **SBE-16 (Conductivity-Temperature):** 5-minute sampling interval (Stratus 12-13)
- **SBE-37 (Conductivity-Temperature-Pressure):** 30-minute sampling interval (Stratus 14-22)

---

## Notes for Future Reference

1. **Data Report Files:** The `*_data_report.tex` files in each deployment folder contain some redundant content with the main chapter files. Both sets were updated to maintain consistency.

2. **QC Limitations:** The added documentation in Stratus 15, 18, 19 chapters acknowledges that automated spike detection may miss:
   - Transients at deployment/recovery boundaries
   - Gradual step-like changes
   - Edge artifacts from rolling-window statistics

3. **Plotting Code:** The updated deployment-location plotting function now uses open markers by default, which can be applied consistently across all visualization functions that need to show overlapping points.

---

## Files Location
All source files are located in:
- LaTeX chapters: `/Users/yugao/UOP/ORS-processing/doc/Stratus/WHOI_technical_report/`
- Processing code: `/Users/yugao/UOP/ORS-processing/src/`
- Final PDF: `/Users/yugao/UOP/ORS-processing/doc/Stratus/WHOI_technical_report/stratus_technical_report.pdf`
