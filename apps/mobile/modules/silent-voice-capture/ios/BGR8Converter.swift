import Foundation
import CryptoKit

enum BGR8ConversionError: Error { case dimensions, stride, buffer }

enum BGR8Converter {
  /// Literal BGRA -> packed BGR. No geometric or color-space transform.
  static func pack(_ source: UnsafeRawBufferPointer, width: Int, height: Int, bytesPerRow: Int) throws -> Data {
    guard width > 0, height > 0, width <= 640, height <= 640, width * height <= 640 * 480 else {
      throw BGR8ConversionError.dimensions
    }
    guard bytesPerRow >= width * 4 else { throw BGR8ConversionError.stride }
    let (rowOffset, overflow1) = (height - 1).multipliedReportingOverflow(by: bytesPerRow)
    let (required, overflow2) = rowOffset.addingReportingOverflow(width * 4)
    guard !overflow1, !overflow2, source.count >= required, let base = source.baseAddress else {
      throw BGR8ConversionError.buffer
    }
    let input = base.assumingMemoryBound(to: UInt8.self)
    var result = Data(count: width * height * 3)
    result.withUnsafeMutableBytes { (output: UnsafeMutableRawBufferPointer) in
      let target = output.baseAddress!.assumingMemoryBound(to: UInt8.self)
      for y in 0..<height {
        for x in 0..<width {
          let src = y * bytesPerRow + x * 4
          let dst = (y * width + x) * 3
          target[dst] = input[src]
          target[dst + 1] = input[src + 1]
          target[dst + 2] = input[src + 2]
        }
      }
    }
    return result
  }

  /// This is the ONLY path that hashes pixels: all inputs are arithmetic, not camera data.
  static func syntheticReport() throws -> [String: Any] {
    let width = 640, height = 480, stride = 2576
    var source = [UInt8](repeating: 231, count: stride * height)
    for y in 0..<height {
      for x in 0..<width {
        let i = y * stride + x * 4
        source[i] = UInt8((x + 3 * y) % 256)
        source[i + 1] = UInt8((5 * x + y) % 256)
        source[i + 2] = UInt8((7 * x + 11 * y) % 256)
        source[i + 3] = UInt8((x ^ y) % 256)
      }
    }
    let bgr = try source.withUnsafeBytes { try pack($0, width: width, height: height, bytesPerRow: stride) }
    let offsets = [0, 1, 2, 3, 4, 5, 1917, 1918, 1919, 1920, 1921, 1922, 461760, 461761, 461762, 921597, 921598, 921599]
    return [
      "width": width, "height": height, "pixelFormat": "BGR8", "byteCount": bgr.count,
      "sha256": SHA256.hash(data: bgr).map { String(format: "%02x", $0) }.joined(),
      "samples": offsets.map { ["offset": $0, "value": Int(bgr[$0])] }
    ]
  }
}
