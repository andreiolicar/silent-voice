enum CaptureSide: String { case landscapeLeft, landscapeRight }

enum CapturePosture {
  case portrait, landscapeLeft, landscapeRight, unknown
  // UIDevice orientation names are the inverse of AVCapture's landscape names.
  var captureSide: CaptureSide? {
    switch self {
    case .landscapeLeft: return .landscapeRight
    case .landscapeRight: return .landscapeLeft
    default: return nil
    }
  }
}
