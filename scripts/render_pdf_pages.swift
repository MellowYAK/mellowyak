import AppKit
import Foundation
import PDFKit

guard CommandLine.arguments.count == 3 else {
    fputs("usage: render_pdf_pages.swift INPUT.pdf OUTPUT_DIR\n", stderr)
    exit(2)
}

let input = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
guard let document = PDFDocument(url: input) else {
    fputs("unable to open PDF\n", stderr)
    exit(3)
}

for index in 0..<document.pageCount {
    guard let page = document.page(at: index) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let scale = min(2.0, 1800.0 / max(bounds.width, bounds.height))
    let width = max(1, Int(bounds.width * scale))
    let height = max(1, Int(bounds.height * scale))
    let image = page.thumbnail(
        of: NSSize(width: width, height: height),
        for: .mediaBox
    )
    guard
        let tiff = image.tiffRepresentation,
        let bitmap = NSBitmapImageRep(data: tiff),
        let data = bitmap.representation(using: .png, properties: [:])
    else { continue }
    let filename = String(format: "page-%03d.png", index + 1)
    try data.write(to: output.appendingPathComponent(filename))
}

print("pages=\(document.pageCount)")
