import Foundation
import XCTest
@testable import CaptureCore

final class BGR8ConverterTests: XCTestCase {
  func testPreservesBGRSpatialOrderAndIgnoresAlphaAndRowPadding() throws {
    let input: [UInt8] = [1, 2, 3, 99, 4, 5, 6, 0, 231, 231, 231, 231,
                         7, 8, 9, 255, 10, 11, 12, 44]
    let output = try input.withUnsafeBytes {
      try BGR8Converter.pack($0, width: 2, height: 2, bytesPerRow: 12)
    }
    XCTAssertEqual(Array(output), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
  }

  func testRejectsTruncationInvalidStrideDimensionsAndOverflow() {
    let bytes = [UInt8](repeating: 1, count: 32)
    for (width, height, stride) in [(2,2,12), (2,1,7), (0,1,4), (-1,1,4), (641,480,2564), (640,641,2560), (2,3,Int.max)] {
      let size = width == 2 && height == 2 ? 19 : bytes.count
      XCTAssertThrowsError(try Array(bytes.prefix(size)).withUnsafeBytes {
        try BGR8Converter.pack($0, width: width, height: height, bytesPerRow: stride)
      })
    }
  }

  func testFullSyntheticFrameMatchesIndependentPythonReferenceExactly() throws {
    let fixtureURL = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
      .appendingPathComponent("../../../src/features/visual-recognition/data/bgr8-reference.json").standardized
    let expected = try JSONSerialization.jsonObject(with: Data(contentsOf: fixtureURL)) as! [String: Any]
    let actual = try BGR8Converter.syntheticReport()
    XCTAssertEqual(actual["sha256"] as? String, expected["sha256"] as? String)
    XCTAssertEqual(actual["byteCount"] as? Int, 921600)
    XCTAssertEqual(actual["samples"] as? [[String: Int]], expected["samples"] as? [[String: Int]])
  }

  func testOnlyKnownLandscapePosturesCanProduceUprightCapture() {
    XCTAssertEqual(CapturePosture.landscapeLeft.captureSide, .landscapeRight)
    XCTAssertEqual(CapturePosture.landscapeRight.captureSide, .landscapeLeft)
    XCTAssertNil(CapturePosture.portrait.captureSide)
    XCTAssertNil(CapturePosture.unknown.captureSide)
  }
}
