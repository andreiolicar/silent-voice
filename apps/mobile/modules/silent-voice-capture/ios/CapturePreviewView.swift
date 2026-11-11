import AVFoundation
import ExpoModulesCore

final class CapturePreviewView: ExpoView {
  let controller = CaptureController()
  private lazy var preview = AVCaptureVideoPreviewLayer(session: controller.session)
  private var orientationObserver: NSObjectProtocol?
  private var monitoringOrientation = false
  private var normalizedDeviceOrientation: UIDeviceOrientation?

  required init(appContext: AppContext? = nil) {
    super.init(appContext: appContext)
    clipsToBounds = true
    backgroundColor = .black
    preview.videoGravity = .resizeAspect
    layer.addSublayer(preview)
  }

  override func layoutSubviews() {
    super.layoutSubviews()
    preview.frame = bounds
    if let connection = preview.connection {
      if connection.isVideoOrientationSupported { connection.videoOrientation = .portrait }
      if connection.isVideoMirroringSupported {
        connection.automaticallyAdjustsVideoMirroring = false
        connection.isVideoMirrored = true
      }
    }
  }

  override func didMoveToWindow() {
    super.didMoveToWindow()
    if window == nil {
      controller.cancel()
      normalizedDeviceOrientation = nil
      if let observer = orientationObserver { NotificationCenter.default.removeObserver(observer) }
      orientationObserver = nil
      if monitoringOrientation { UIDevice.current.endGeneratingDeviceOrientationNotifications() }
      monitoringOrientation = false
    } else if !monitoringOrientation {
      UIDevice.current.beginGeneratingDeviceOrientationNotifications()
      monitoringOrientation = true
      orientationObserver = NotificationCenter.default.addObserver(forName: UIDevice.orientationDidChangeNotification, object: nil, queue: .main) { [weak self] _ in
        DispatchQueue.main.async { [weak self] in
          guard let self, let initial = self.normalizedDeviceOrientation else { return }
          if UIDevice.current.orientation != initial {
            self.normalizedDeviceOrientation = nil
            self.controller.cancel()
          }
        }
      }
    }
  }

  func capture(_ promise: Promise) {
    guard window != nil, UIApplication.shared.applicationState == .active else {
      promise.resolve(["status": "cancelled", "frames": [], "readFailures": 0])
      return
    }
    normalizedDeviceOrientation = nil
    controller.capture(started: { [weak self] in self?.setNeedsLayout() }) { report in promise.resolve(report) }
  }

  func captureNormalized(_ promise: Promise) {
    guard window != nil, UIApplication.shared.applicationState == .active else {
      promise.resolve(["status": "cancelled", "frames": [], "readFailures": 0])
      return
    }
    let deviceOrientation = UIDevice.current.orientation
    let posture: CapturePosture
    switch deviceOrientation {
    case .landscapeLeft: posture = .landscapeLeft
    case .landscapeRight: posture = .landscapeRight
    case .portrait, .portraitUpsideDown: posture = .portrait
    default: posture = .unknown
    }
    guard let side = posture.captureSide else {
      promise.resolve(["status": "camera-error", "error": "camera-orientation", "frames": [], "readFailures": 0])
      return
    }
    normalizedDeviceOrientation = deviceOrientation
    let orientation: AVCaptureVideoOrientation = side == .landscapeLeft ? .landscapeLeft : .landscapeRight
    controller.capture(orientation: orientation, normalizeBGR: true, started: { [weak self] in self?.setNeedsLayout() }) { [weak self] report in
      self?.normalizedDeviceOrientation = nil
      promise.resolve(report)
    }
  }

  deinit {
    controller.cancel()
    if let observer = orientationObserver { NotificationCenter.default.removeObserver(observer) }
    if monitoringOrientation { DispatchQueue.main.async { UIDevice.current.endGeneratingDeviceOrientationNotifications() } }
  }
}
