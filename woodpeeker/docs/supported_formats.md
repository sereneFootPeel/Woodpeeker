# Supported Formats

## Audio (FFmpeg)
- Input/Output: mp3, wav, flac, aac, ogg, m4a

## NCM (ncmdump + FFmpeg)
- Input: ncm
- Output: mp3, wav, flac, aac, ogg, m4a

## Video (FFmpeg)
- Input/Output: mp4, mkv, avi, mov, webm

## Text/Document (Pandoc)
- Input: txt, md, markdown, html, docx, odt, rtf
- Output: txt, md, html, docx, odt, rtf, pdf

## Text -> Ebook (Pandoc + Calibre)
- Input: txt, md, markdown, html, docx, odt, rtf
- Output: epub, mobi, azw3

## Office/PDF (LibreOffice)
- Input: doc, docx, ppt, pptx, xls, xlsx, odt, rtf
- Output: pdf, docx, odt, rtf, html, txt

## Ebook (Calibre)
- Input: epub, mobi, azw3, pdf
- Output: epub, mobi, azw3, pdf, txt

## Image (ImageMagick)
- Input/Output: jpg, jpeg, png, webp, gif, bmp, tif, tiff, avif, heic, svg, ico
- Folder input to PDF: a folder containing images -> pdf (merged in filename order)

## Notes
- Actual compatibility depends on installed converter version and source file content.
- For PDF writing via Pandoc, a PDF engine may be required.
- Route selection supports direct conversion and up to 2-hop chains (one intermediate format).
- Example: `mobi -> txt` is directly supported by Calibre (no intermediate step required).
