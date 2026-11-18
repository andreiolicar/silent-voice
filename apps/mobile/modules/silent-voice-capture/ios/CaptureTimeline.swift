enum CaptureTimelineError: Error {
  case invalidTimestamp, nonMonotonic, frameLimit
}

/// Integer arithmetic only. The caller converts the returned relative value to JS.
struct CaptureTimeline {
  private var origin: Int64?
  private var previous: Int64?
  private(set) var count = 0
  private var elapsed: Int64 = 0
  var isComplete: Bool { elapsed >= 4_000_000_000 }

  mutating func append(_ timestamp: Int64) throws -> Int64 {
    guard timestamp >= 0 else { throw CaptureTimelineError.invalidTimestamp }
    guard count < 256 else { throw CaptureTimelineError.frameLimit }
    if let previous, timestamp <= previous { throw CaptureTimelineError.nonMonotonic }
    let relative = timestamp - (origin ?? timestamp)
    guard relative >= 0, relative <= 8_000_000_000 else {
      throw CaptureTimelineError.invalidTimestamp
    }
    if origin == nil { origin = timestamp }
    previous = timestamp
    elapsed = relative
    count += 1
    return relative
  }
}
