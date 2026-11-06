# Print Wraparound Cover Geometry (`LTR` vs `RTL`)

## 1. Panel Coordinate Formulas (`Paperback` with `0.125"` Bleed)

Let:
- $W_t, H_t$ = Trim width and height in inches
- $B = 0.125\text{ in}$ (`3.175 mm`) = Outer bleed on top, bottom, left, and right
- $N$ = Actual even page count of `dist/interior-paperback.pdf`
- $C$ = Paper stock caliper (`0.002252"` white, `0.002500"` cream, `0.002347"` premium color)
- $S = N \times C$ = Spine width in inches

Then:
- $\text{Total Width } W_{\text{full}} = 2B + 2W_t + S$
- $\text{Total Height } H_{\text{full}} = 2B + H_t$

### English / Latin (`direction: "ltr"`)
```text
|<-- B -->|<------ Wt (Back Cover) ------>|<-- S -->|<------ Wt (Front Cover) ----->|<-- B -->|
|         |   [blurb]                     |  SPINE  |         BOOK TITLE            |         |
|         |              [Barcode 2x1.2"] |         |         Author Name           |         |
```

### Arabic / Right-to-Left (`direction: "rtl"`)
```text
|<-- B -->|<----- Wt (Front Cover) ------>|<-- S -->|<------ Wt (Back Cover) ------>|<-- B -->|
|         |         عنوان الكتاب          |  الكعب  |   [نبذة الغلاف الخلفي]        |         |
|         |          اسم المؤلف           |         | [Barcode 2x1.2"]              |         |
```

## 2. Safe Zones & Barcode Keepout

- **Outer Live Safe Margin:** Keep all text at least `0.25 in` (`6.35 mm`) inside the trim line (`0.375 in` from outer bleed edge).
- **Spine Hinge Safe Margin:** Keep front/back cover text at least `0.25 in` away from spine fold lines; keep spine lettering (when $N \ge 79$) at least `0.0625 in` (`1.6 mm`) inside both spine folds.
- **ISBN Barcode Keepout (`2.0 in × 1.2 in`):** Positioned in the bottom zone of the Back Cover (`>= 0.25 in` above bottom trim and `>= 0.25 in` away from spine hinge and outer trim). Must contain solid light fill and **zero overlapping cover text**.
