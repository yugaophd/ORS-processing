# NTAS Technical Report - Reviewer Edits Summary

**Report:** Northwest Tropical Atlantic Station (NTAS): Deep-Ocean Temperature and Salinity Data Deployments 11–20 (2011–2022)

**Date Completed:** June 29, 2026

---

## Completed Tasks

### 1. ✅ Abstract & Introduction Edits
- **Water Depth:** Added "approximately 5118 m water depth" to abstract
- **NOAA Support:** Added "With support from the NOAA Global Ocean Monitoring and Observing Program" to introduction
- **NTAS Station Description:** Updated with specific water depths
  - Average water depth: 5118 m
  - Instrument depth range: 4936 m to 5016 m

### 2. ✅ Deployment Strategy Terminology
- **Change:** "serviced repeatedly" → "serviced on a (nominal) annual cycle"
- **Enhancement:** "overlap periods of hours to days" qualifier added
- **File:** `00/introduction_chapter.tex`

### 3. ✅ Server Reference Replacement
- **Instances:** 9 replacements across 9 chapters
- **Change:** report text updated to reference the UOP server
- **Files Modified:** NTAS 11, 12, 13, 14, 16, 17, 18, 19, 20 chapters
- **Context:** "recover.xls spreadsheet on the UOP server"

### 4. ✅ Deployment-Specific Time Correction Wording
- **NTAS 13:** Changed from "+/- 30 minutes for NTAS deployments" → "+/- 30 minutes for NTAS 13 deployment"
- **NTAS 12 & 14:** Already deployment-specific (no changes needed)
- **Files Modified:** 1 file (ntas13_chapter.tex)

### 5. ✅ NTAS 12 Data Quality Clarifications
- **Table Caption:** Added "Only one instrument returned valid data for this deployment"
- **Figure Caption:** Added note that only SBE16 1877 returned usable data
- **Spike Removal Section:** Added "SBE16 1878 did not return usable data and was eliminated from further processing"
- **Files Modified:** 2 files (12/ntas12_chapter.tex, 12/spike_stats.tex)

### 6. ✅ Overlap Figure Caption Corrections
- **Change:** Removed misleading text about vertical dashed lines
- **Removed Text:** "The vertical dashed lines indicate: start of new deployment, optimal merge point, and end of previous deployment"
- **Chapters Updated:** 7 (NTAS 12, 13, 14, 17, 18, 19, 20)
- **Reason:** Dashed lines were not visible in simplified captions

### 7. ✅ Spike-Removal Window Duration Corrections
- **NTAS 14:** Changed "6 hours" → "2 hours"
- **NTAS 16-20:** Changed "6 hours" → "1 hour" (each deployment)
- **NTAS 12-13:** Left unchanged (6 hours is correct for those deployments)
- **Total Updates:** 6 files

### 8. ✅ NTAS 19 Recovery Spike Plot Verification
- **Recovery Spike Duration:** 6 seconds (2021-11-14 21:50:40 to 21:50:46)
- **Spike Display:** "0h 0m" (correct for sub-minute duration)
- **Plot Window:** 2-hour buffer around spike times for context
- **Figures Regenerated:** 2 spike plot images (SN 12246, SN 12247)

---

## Modified Files Summary

| Category | Count | Examples |
|----------|-------|----------|
| Main chapter files | 10 | ntas11_chapter.tex – ntas20_chapter.tex |
| Introduction file | 1 | 00/introduction_chapter.tex |
| Support files | 1 | 12/spike_stats.tex |
| **Total LaTeX** | **12** | — |
| Figures regenerated | 2 | ntas19_12246_spikes.png, ntas19_12247_spikes.png |

---

## Build & Verification Results

✅ **PDF Compilation:** Successful  
✅ **Page Count:** 160 pages  
✅ **File Size:** 48.9 MB  
✅ **LaTeX Errors:** None  
✅ **Cross-references:** All updated  

### Verification Checklist
- ✅ Report text now references the UOP server
- ✅ All "the UOP server" replacements confirmed (9 instances)
- ✅ "serviced on a (nominal) annual cycle" found (1 instance)
- ✅ Water depth of 5118 m added to abstract
- ✅ Deployment-specific wording applied
- ✅ NTAS 12 clarifications added
- ✅ Overlap captions simplified
- ✅ Spike-removal windows corrected

---

## Technical Details

### Deployment-Specific Sample Intervals
- **NTAS 11-20:** Mix of SBE-16 and SBE-37 instruments
- **Time Correction:** Uses deployment-specific sample intervals (varies by deployment)
- **Overlap Detection:** Annual service cycle with hours-to-days overlap periods

### NTAS 12 Instrument Issue
Only one instrument (SBE16 1877) returned usable data for this deployment. SBE16 1878 failed to return valid readings and was excluded from processing and comparisons.

### Salinity Calculation
- Method: Fixed pressure from instrument depth using TEOS-10
- Implementation: Avoids drift issues in measured pressure data
- Coordinates: Latitude/longitude from anchor survey positions

---

## Notes for Future Reference

1. **Overlap Figures:** The simplified captions for overlap figures were removed because the dashed line visual indicators were not consistently visible in all viewing contexts.

2. **Spike-Removal Windows:** Duration varies by deployment based on actual spike characteristics:
   - 6 hours: NTAS 11, 12, 13, 15 (deployment-specific)
   - 2 hours: NTAS 14
   - 1 hour: NTAS 16, 17, 18, 19, 20

3. **NTAS 19 Recovery Spike:** The 6-second recovery spike is correctly captured and displayed. The "0h 0m" duration indicates the spike is shorter than 1 minute, which is accurately represented in figures.

---

## Files Location
All source files are located in:
- LaTeX chapters: `/Users/yugao/UOP/ORS-processing/doc/NTAS/WHOI_technical_report/`
- Final PDF: `/Users/yugao/UOP/ORS-processing/doc/NTAS/WHOI_technical_report/NTAS_technical_report.pdf`
