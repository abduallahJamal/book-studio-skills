# EPUB 3.3 (`RTL`/`LTR`) & Static Web Book Specifications

## 1. Critical EPUB 3 Packaging Rules

1. **Archive Entry #0 (`mimetype`):** Must be the very first entry in the ZIP container, stored uncompressed (`ZIP_STORED`), with exact ASCII payload `application/epub+zip` (20 bytes, no trailing newline).
2. **`META-INF/container.xml`:** Points to `OEBPS/content.opf`.
3. **`OEBPS/content.opf` (`version="3.0"`):**
   - Required Dublin Core tags: `dc:identifier`, `dc:title`, `dc:language`, `dc:creator`, plus `<meta property="dcterms:modified">YYYY-MM-DDTHH:MM:SSZ</meta>`.
   - Arabic books MUST set `<spine page-progression-direction="rtl">`; omitting this forces Arabic readers to swipe backward on Kindle, Kobo, and Apple Books.
   - Any XHTML document containing `<math>` MUST declare `properties="mathml"` on its `<item>` in `<manifest>`, and `OEBPS/nav.xhtml` MUST declare `properties="nav"`.
   - Any XHTML document referencing inline `<svg>` or `.svg` images works cleanly across modern EPUB 3 engines.

## 2. Reflowable E-Reader CSS Guardrails

- Never hardcode fixed `px` widths or `color: #000000; background: #FFFFFF` on `body` in EPUB CSS — doing so breaks Dark/Night mode in Kindle and Apple Books! Use relative `em`/`rem` units and inherit foreground text colors.
- Isolate code blocks with `direction: ltr; text-align: left; unicode-bidi: embed;` so brackets and operators inside Arabic books render accurately.
