import AVFoundation
import ExpoModulesCore

func capturePermission() -> String {
  switch AVCaptureDevice.authorizationStatus(for: .video) {
  case .authorized: return "granted"
  case .notDetermined: return "undetermined"
  case .restricted: return "restricted"
  default: return "denied"
  }
}

public final class SilentVoiceCaptureModule: Module {
  public func definition() -> ModuleDefinition {
    Name("SilentVoiceCapture")

    AsyncFunction("getPermission") { () -> String in capturePermission() }
    AsyncFunction("syntheticNormalization") { () throws -> [String: Any] in
      try BGR8Converter.syntheticReport()
    }

    AsyncFunction("requestPermission") { (promise: Promise) in
      AVCaptureDevice.requestAccess(for: .video) { _ in
        promise.resolve(capturePermission())
      }
    }

    AsyncFunction("syntheticFrames") { () throws -> [[String: Any]] in
      var timeline = CaptureTimeline()
      let origin: Int64 = 9_000_000_000_000_000_000
      return try (0...120).map { index in
        let absolute = origin + (Int64(index) * 1_000_000_000 + 15) / 30
        return [
          "timestampNs": Double(try timeline.append(absolute)),
          "width": 640, "height": 480, "pixelFormat": "BGR8",
          "orientation": "upright", "mirrored": false
        ]
      }
    }

    View(CapturePreviewView.self) {
      AsyncFunction("capture") { (view: CapturePreviewView, promise: Promise) in
        view.capture(promise)
      }
      AsyncFunction("cancel") { (view: CapturePreviewView, promise: Promise) in
        view.controller.cancel { promise.resolve() }
      }
      AsyncFunction("captureNormalized") { (view: CapturePreviewView, promise: Promise) in
        view.captureNormalized(promise)
      }
    }
  }
}
