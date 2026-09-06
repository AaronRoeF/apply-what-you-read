// Apple Vision OCR — batch text recognition over raster images.
// Reads newline-delimited image paths on stdin, emits one JSON object per line on stdout.
// Build: swiftc -O -o ocr_vision ocr_vision.swift
//
// Emits per image: recognized text, mean/min confidence, observation count, pixel dims.
// Confidence is the calibration input for the purge gate — never discard it.

import Foundation
import Vision
import AppKit

func jsonEscape(_ s: String) -> String {
    var o = ""
    for c in s.unicodeScalars {
        switch c {
        case "\"": o += "\\\""
        case "\\": o += "\\\\"
        case "\n": o += "\\n"
        case "\r": o += "\\r"
        case "\t": o += "\\t"
        default:
            if c.value < 0x20 { o += String(format: "\\u%04x", c.value) } else { o.unicodeScalars.append(c) }
        }
    }
    return o
}

func emit(_ fields: [(String, String)]) {
    print("{" + fields.map { "\"\($0.0)\":\($0.1)" }.joined(separator: ",") + "}")
}

func str(_ s: String) -> String { "\"\(jsonEscape(s))\"" }

func process(_ path: String) {
    let url = URL(fileURLWithPath: path)
    guard let img = NSImage(contentsOf: url),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        emit([("path", str(path)), ("ok", "false"), ("error", str("unreadable"))])
        return
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    if #available(macOS 13.0, *) { req.automaticallyDetectsLanguage = true }

    do {
        try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    } catch {
        emit([("path", str(path)), ("ok", "false"), ("error", str("\(error)"))])
        return
    }

    let obs = (req.results as? [VNRecognizedTextObservation]) ?? []
    var lines: [String] = []
    var confs: [Float] = []
    for o in obs {
        guard let top = o.topCandidates(1).first else { continue }
        lines.append(top.string)
        confs.append(top.confidence)
    }
    let text = lines.joined(separator: "\n")
    let mean = confs.isEmpty ? 0 : confs.reduce(0, +) / Float(confs.count)
    let minc = confs.min() ?? 0

    emit([
        ("path", str(path)),
        ("ok", "true"),
        ("width", "\(cg.width)"),
        ("height", "\(cg.height)"),
        ("n_obs", "\(obs.count)"),
        ("mean_conf", String(format: "%.4f", mean)),
        ("min_conf", String(format: "%.4f", minc)),
        ("chars", "\(text.count)"),
        ("text", str(text)),
    ])
}

while let line = readLine(strippingNewline: true) {
    let p = line.trimmingCharacters(in: .whitespaces)
    if !p.isEmpty { process(p) }
}
