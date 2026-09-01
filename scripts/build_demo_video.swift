#!/usr/bin/env swift

import AVFoundation
import CoreGraphics
import CoreText
import Foundation
import ImageIO

let projectRoot = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let researchURL = projectRoot.appendingPathComponent("docs/assets/research-page.png")
let skillLabURL = projectRoot.appendingPathComponent("docs/assets/skill-lab-page.png")
let outputURL = projectRoot.appendingPathComponent("docs/assets/researchforge-v1.4-demo.mp4")

guard !FileManager.default.fileExists(atPath: outputURL.path) else {
    fatalError("Refusing to overwrite existing demo video: \(outputURL.path)")
}

func loadImage(_ url: URL) -> CGImage {
    guard
        let source = CGImageSourceCreateWithURL(url as CFURL, nil),
        let image = CGImageSourceCreateImageAtIndex(source, 0, nil)
    else {
        fatalError("Cannot load image: \(url.path)")
    }
    return image
}

let researchImage = loadImage(researchURL)
let skillLabImage = loadImage(skillLabURL)
let width = 1280
let height = 720
let fps: Int32 = 30
let framesPerScene = Int(fps) * 6

let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mp4)
let input = AVAssetWriterInput(
    mediaType: .video,
    outputSettings: [
        AVVideoCodecKey: AVVideoCodecType.h264,
        AVVideoWidthKey: width,
        AVVideoHeightKey: height,
        AVVideoCompressionPropertiesKey: [
            AVVideoAverageBitRateKey: 4_000_000,
            AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
        ],
    ]
)
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(
    assetWriterInput: input,
    sourcePixelBufferAttributes: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
        kCVPixelBufferWidthKey as String: width,
        kCVPixelBufferHeightKey as String: height,
    ]
)
guard writer.canAdd(input) else { fatalError("Cannot add video input") }
writer.add(input)
guard writer.startWriting() else { fatalError(writer.error?.localizedDescription ?? "Writer failed") }
writer.startSession(atSourceTime: .zero)

func drawLabel(_ text: String, in context: CGContext) {
    context.saveGState()
    context.setFillColor(CGColor(red: 0.03, green: 0.07, blue: 0.09, alpha: 0.88))
    context.fill(CGRect(x: 0, y: 0, width: width, height: 54))
    let attributes: [CFString: Any] = [
        kCTFontAttributeName: CTFontCreateWithName("Menlo" as CFString, 20, nil),
        kCTForegroundColorAttributeName: CGColor(
            red: 0.35, green: 0.90, blue: 0.72, alpha: 1
        ),
    ]
    let line = CTLineCreateWithAttributedString(
        CFAttributedStringCreate(nil, text as CFString, attributes as CFDictionary)
    )
    context.textPosition = CGPoint(x: 28, y: 17)
    CTLineDraw(line, context)
    context.restoreGState()
}

func makeBuffer(image: CGImage, label: String, progress: CGFloat) -> CVPixelBuffer {
    var optionalBuffer: CVPixelBuffer?
    guard
        let pool = adaptor.pixelBufferPool,
        CVPixelBufferPoolCreatePixelBuffer(nil, pool, &optionalBuffer) == kCVReturnSuccess,
        let buffer = optionalBuffer
    else {
        fatalError("Cannot allocate video frame")
    }
    CVPixelBufferLockBaseAddress(buffer, [])
    defer { CVPixelBufferUnlockBaseAddress(buffer, []) }
    guard
        let base = CVPixelBufferGetBaseAddress(buffer),
        let context = CGContext(
            data: base,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue
                | CGBitmapInfo.byteOrder32Little.rawValue
        )
    else {
        fatalError("Cannot create frame context")
    }
    context.setFillColor(CGColor(red: 0.027, green: 0.063, blue: 0.082, alpha: 1))
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    let baseScale = max(
        CGFloat(width) / CGFloat(image.width),
        CGFloat(height) / CGFloat(image.height)
    )
    let zoom = 1 + progress * 0.035
    let drawWidth = CGFloat(image.width) * baseScale * zoom
    let drawHeight = CGFloat(image.height) * baseScale * zoom
    let drawRect = CGRect(
        x: (CGFloat(width) - drawWidth) / 2,
        y: (CGFloat(height) - drawHeight) / 2,
        width: drawWidth,
        height: drawHeight
    )
    context.interpolationQuality = .high
    context.draw(image, in: drawRect)
    drawLabel(label, in: context)
    return buffer
}

let scenes = [
    (researchImage, "RESEARCHFORGE V1.4  /  RESEARCH WORKSPACE"),
    (skillLabImage, "RESEARCHFORGE V1.4  /  CONTROLLED SKILL LAB"),
]
var frameNumber: Int64 = 0
for (image, label) in scenes {
    for sceneFrame in 0..<framesPerScene {
        while !input.isReadyForMoreMediaData { Thread.sleep(forTimeInterval: 0.002) }
        let progress = CGFloat(sceneFrame) / CGFloat(framesPerScene - 1)
        let buffer = makeBuffer(image: image, label: label, progress: progress)
        let time = CMTime(value: frameNumber, timescale: fps)
        guard adaptor.append(buffer, withPresentationTime: time) else {
            fatalError(writer.error?.localizedDescription ?? "Cannot append video frame")
        }
        frameNumber += 1
    }
}
input.markAsFinished()
let completion = DispatchSemaphore(value: 0)
writer.finishWriting { completion.signal() }
completion.wait()
guard writer.status == .completed else {
    fatalError(writer.error?.localizedDescription ?? "Video did not complete")
}
print(outputURL.path)
