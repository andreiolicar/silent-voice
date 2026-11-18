import XCTest
@testable import CaptureCore

final class CaptureTimelineTests: XCTestCase {
  func testSubtractsLargeOriginBeforeConversion() throws {
    var timeline = CaptureTimeline()
    let origin: Int64 = 9_000_000_000_000_000_000
    XCTAssertEqual(try timeline.append(origin), 0)
    XCTAssertEqual(try timeline.append(origin + 33_333_333), 33_333_333)
    XCTAssertEqual(try timeline.append(origin + 4_000_000_000), 4_000_000_000)
    XCTAssertTrue(timeline.isComplete)
    XCTAssertEqual(timeline.count, 3)
  }

  func testRejectsNegativeRepeatedAndRegressiveTimes() throws {
    var timeline = CaptureTimeline()
    XCTAssertThrowsError(try timeline.append(-1))
    XCTAssertEqual(try timeline.append(50), 0)
    XCTAssertThrowsError(try timeline.append(50))
    XCTAssertThrowsError(try timeline.append(49))
    XCTAssertEqual(timeline.count, 1)
  }

  func testCompletesAtFourSecondsAndResetsForNextCapture() throws {
    var timeline = CaptureTimeline()
    _ = try timeline.append(100)
    _ = try timeline.append(4_000_000_099)
    XCTAssertFalse(timeline.isComplete)
    _ = try timeline.append(4_000_000_100)
    XCTAssertTrue(timeline.isComplete)
    timeline = CaptureTimeline()
    XCTAssertFalse(timeline.isComplete)
    XCTAssertEqual(try timeline.append(900), 0)
    XCTAssertEqual(timeline.count, 1)
  }

  func testBoundsMemoryAndClockRange() throws {
    var timeline = CaptureTimeline()
    for time in 0..<256 { _ = try timeline.append(Int64(time)) }
    XCTAssertThrowsError(try timeline.append(256))
    XCTAssertEqual(timeline.count, 256)
    var clock = CaptureTimeline()
    _ = try clock.append(0)
    XCTAssertThrowsError(try clock.append(8_000_000_001))
  }
}
