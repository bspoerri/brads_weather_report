"""
Render the text report to a PDF.

Primary path uses macOS AppKit (CoreText), which lays the report out
in a monospaced font with full color-emoji support and no third-party
dependencies. If AppKit is unavailable (e.g. a headless context), it
falls back to the `cupsfilter` CLI for a plain monospaced PDF.
"""
import os
import html

PAGE_WIDTH_PT = 612.0   # US Letter width (8.5 in * 72)
FONT_SIZE_PT  = 11


def _appkit_pdf(text, path):
    """Render `text` to a PDF via AppKit/CoreText (monospaced, with
    color-emoji support). Raises if AppKit isn't usable."""
    import AppKit
    from AppKit import NSTextView, NSMakeRect
    from Foundation import NSAttributedString

    # The charset must be declared, or AppKit decodes the UTF-8 bytes
    # as Latin-1 and the emoji turn into mojibake.
    doc = (f'<!DOCTYPE html><html><head>'
           f'<meta charset="utf-8"></head><body>'
           f'<pre style="font-family:Menlo,monospace; '
           f'font-size:{FONT_SIZE_PT}px; line-height:1.3">'
           f'{html.escape(text)}</pre></body></html>')
    data = (AppKit.NSString.stringWithString_(doc)
            .dataUsingEncoding_(AppKit.NSUTF8StringEncoding))
    attr, _ = NSAttributedString.alloc().initWithHTML_documentAttributes_(
        data, None)
    if attr is None:
        raise RuntimeError('could not build attributed string from HTML')

    view = NSTextView.alloc().initWithFrame_(
        NSMakeRect(0, 0, PAGE_WIDTH_PT, 10))
    view.textStorage().setAttributedString_(attr)
    view.setVerticallyResizable_(True)
    view.sizeToFit()
    # Force layout so the height reflects the wrapped content.
    view.layoutManager().glyphRangeForTextContainer_(view.textContainer())
    height = view.frame().size.height + 24

    pdf = view.dataWithPDFInsideRect_(
        NSMakeRect(0, 0, PAGE_WIDTH_PT, height))
    if not pdf.writeToFile_atomically_(path, True):
        raise RuntimeError('failed to write PDF data')


def _cupsfilter_pdf(text, path):
    """Fallback: render `text` to a plain monospaced PDF with the
    `cupsfilter` CLI (no emoji, but works headless)."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile('w', suffix='.txt',
                                     delete=False, encoding='utf-8') as f:
        f.write(text)
        txt_path = f.name
    try:
        with open(path, 'wb') as out:
            subprocess.run(['cupsfilter', '-i', 'text/plain', txt_path],
                           stdout=out, stderr=subprocess.DEVNULL, check=True)
    finally:
        os.remove(txt_path)


def save_pdf(text, path):
    """Write `text` to `path` as a PDF. Returns the path."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    try:
        _appkit_pdf(text, path)
    except Exception as e:
        print(f'PDF: AppKit render unavailable ({e}); using cupsfilter.')
        _cupsfilter_pdf(text, path)
    return path
