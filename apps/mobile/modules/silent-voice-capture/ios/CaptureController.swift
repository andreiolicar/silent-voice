import AVFoundation
import UIKit

/// No image buffers leave a callback. Only bounded metadata is retained.
final class CaptureController: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
  let session = AVCaptureSession()
  private let queue = DispatchQueue(label: "br.com.silentvoice.capture", qos: .userInitiated)
  private let output = AVCaptureVideoDataOutput()
  private var configured = false
  private var timeline = CaptureTimeline()
  private var frames: [[String: Any]] = []
  private var readFailures = 0
  private var completion: (([String: Any]) -> Void)?
  private var finishing = false
  private var deadline: DispatchWorkItem?
  private var observers: [NSObjectProtocol] = []
  private var normalizeBGR = false
  private var sourceDescriptor: [String: Any]?

  override init() {
    super.init()
    let center = NotificationCenter.default
    observers.append(center.addObserver(forName: UIApplication.willResignActiveNotification, object: nil, queue: nil) { [weak self] _ in
      self?.cancel()
    })
    for name in [AVCaptureSession.wasInterruptedNotification, AVCaptureSession.runtimeErrorNotification] {
      observers.append(center.addObserver(forName: name, object: session, queue: nil) { [weak self] _ in
        self?.queue.async { [weak self] in self?.finish("camera-error", error: "capture-interrupted") }
      })
    }
  }

  deinit {
    observers.forEach { NotificationCenter.default.removeObserver($0) }
    let session = session
    queue.async { if session.isRunning { session.stopRunning() } }
  }

  func capture(orientation: AVCaptureVideoOrientation = .portrait, normalizeBGR: Bool = false, started: @escaping () -> Void, completion: @escaping ([String: Any]) -> Void) {
    queue.async { [self] in
      guard self.completion == nil else {
        DispatchQueue.main.async { completion(["status": "camera-error", "error": "capture-busy", "frames": [], "readFailures": 0]) }
        return
      }
      self.completion = completion
      timeline = CaptureTimeline()
      frames = []
      readFailures = 0
      self.normalizeBGR = normalizeBGR
      sourceDescriptor = nil
      guard capturePermission() == "granted" else {
        finish("camera-error", error: "camera-permission")
        return
      }
      do { try configure() } catch {
        finish("camera-error", error: "camera-configuration")
        return
      }
      guard let connection = output.connection(with: .video), connection.isVideoOrientationSupported,
            !normalizeBGR || orientation == .landscapeLeft || orientation == .landscapeRight else {
        finish("camera-error", error: "camera-orientation")
        return
      }
      connection.videoOrientation = orientation
      let deadline = DispatchWorkItem { [weak self] in self?.finish("camera-error", error: "capture-timeout") }
      self.deadline = deadline
      queue.asyncAfter(deadline: .now() + 8, execute: deadline)
      session.startRunning()
      DispatchQueue.main.async(execute: started)
    }
  }

  func cancel(completion: @escaping () -> Void = {}) {
    queue.async { [self] in
      finish("cancelled")
      queue.async { DispatchQueue.main.async(execute: completion) }
    }
  }

  private func configure() throws {
    guard !configured else { return }
    guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front) else {
      throw CaptureTimelineError.invalidTimestamp
    }
    let input = try AVCaptureDeviceInput(device: camera)
    session.beginConfiguration()
    defer { session.commitConfiguration() }
    guard session.canSetSessionPreset(.vga640x480), session.canAddInput(input) else {
      throw CaptureTimelineError.invalidTimestamp
    }
    session.sessionPreset = .vga640x480
    session.addInput(input)
    guard session.canAddOutput(output) else {
      session.removeInput(input)
      throw CaptureTimelineError.invalidTimestamp
    }
    output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
    output.alwaysDiscardsLateVideoFrames = true
    output.setSampleBufferDelegate(self, queue: queue)
    session.addOutput(output)
    if let connection = output.connection(with: .video) {
      if connection.isVideoOrientationSupported { connection.videoOrientation = .portrait }
      if connection.isVideoMirroringSupported {
        connection.automaticallyAdjustsVideoMirroring = false
        connection.isVideoMirrored = false
      }
    }
    do {
      try camera.lockForConfiguration()
      defer { camera.unlockForConfiguration() }
      if camera.activeFormat.videoSupportedFrameRateRanges.contains(where: { $0.minFrameRate <= 30 && $0.maxFrameRate >= 30 }) {
        camera.activeVideoMinFrameDuration = CMTime(value: 1, timescale: 30)
        camera.activeVideoMaxFrameDuration = CMTime(value: 1, timescale: 30)
      }
    } catch {
      session.removeOutput(output)
      session.removeInput(input)
      throw error
    }
    configured = true
  }

  func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
    guard completion != nil, !finishing else { return }
    guard let image = CMSampleBufferGetImageBuffer(sampleBuffer) else {
      readFailures += 1
      finish("camera-error", error: "missing-pixel-buffer")
      return
    }
    let timestamp = CMTimeConvertScale(CMSampleBufferGetPresentationTimeStamp(sampleBuffer), timescale: 1_000_000_000, method: .roundHalfAwayFromZero)
    guard timestamp.isNumeric else { finish("camera-error", error: "invalid-timestamps"); return }
    do {
      let relative = try timeline.append(timestamp.value)
      let format = CVPixelBufferGetPixelFormatType(image)
      let width = CVPixelBufferGetWidth(image), height = CVPixelBufferGetHeight(image)
      let sourceOrientation: String
      switch connection.videoOrientation {
      case .portrait: sourceOrientation = "portrait"
      case .landscapeLeft: sourceOrientation = "landscapeLeft"
      case .landscapeRight: sourceOrientation = "landscapeRight"
      default: sourceOrientation = "other"
      }
      if sourceDescriptor == nil {
        sourceDescriptor = ["width": width, "height": height,
          "byteCount": CVPixelBufferGetDataSize(image), "bytesPerRow": CVPixelBufferGetBytesPerRow(image),
          "pixelFormat": format == kCVPixelFormatType_32BGRA ? "BGRA32" : "CVPixelFormat-\(format)",
          "orientation": sourceOrientation, "mirrored": connection.isVideoMirrored]
      }
      if normalizeBGR {
        guard width == 640, height == 480, format == kCVPixelFormatType_32BGRA,
              !CVPixelBufferIsPlanar(image), !connection.isVideoMirrored,
              sourceOrientation == "landscapeLeft" || sourceOrientation == "landscapeRight" else {
          finish("camera-error", error: "bgr8-source-incompatible")
          return
        }
        guard CVPixelBufferLockBaseAddress(image, .readOnly) == kCVReturnSuccess else {
          finish("camera-error", error: "pixel-buffer-lock")
          return
        }
        do {
          defer { CVPixelBufferUnlockBaseAddress(image, .readOnly) }
          guard let base = CVPixelBufferGetBaseAddress(image) else { throw BGR8ConversionError.buffer }
          let bytes = UnsafeRawBufferPointer(start: base, count: CVPixelBufferGetDataSize(image))
          let bgr = try BGR8Converter.pack(bytes, width: width, height: height, bytesPerRow: CVPixelBufferGetBytesPerRow(image))
          guard bgr.count == 921600 else { throw BGR8ConversionError.buffer }
          // BGR pixels are ephemeral. No real-image hashes, samples or JS transfer.
          withExtendedLifetime(bgr) {
            frames.append(["timestampNs": Double(relative), "width": 640, "height": 480,
              "pixelFormat": "BGR8", "orientation": "upright", "mirrored": false])
          }
        } catch {
          finish("camera-error", error: "bgr8-conversion")
          return
        }
      } else {
      frames.append([
        "timestampNs": Double(relative), "width": width,
        "height": height,
        "pixelFormat": format == kCVPixelFormatType_32BGRA ? "BGRA32" : "CVPixelFormat-\(format)",
        "orientation": sourceOrientation,
        "mirrored": connection.isVideoMirrored
      ])
      }
      if timeline.isComplete { finish("complete") }
    } catch { finish("camera-error", error: "invalid-timestamps-or-frame-limit") }
  }

  func captureOutput(_ output: AVCaptureOutput, didDrop sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
    if completion != nil, !finishing { readFailures += 1 }
  }

  private func finish(_ status: String, error: String? = nil) {
    guard completion != nil, !finishing else { return }
    finishing = true
    deadline?.cancel()
    deadline = nil
    var report: [String: Any] = ["status": status, "frames": status == "cancelled" ? [] : frames, "readFailures": readFailures]
    if status != "cancelled", let sourceDescriptor { report["source"] = sourceDescriptor }
    if normalizeBGR {
      report["normalization"] = ["status": status == "complete" ? "complete" : "blocked",
        "frameCount": status == "cancelled" ? 0 : frames.count, "byteCountPerFrame": 921600]
    }
    if let error { report["error"] = error }
    let payload = report
    frames.removeAll(keepingCapacity: false)
    // Enqueue stopping so the delegate callback has returned before stopRunning.
    queue.async { [self] in
      if session.isRunning { session.stopRunning() }
      let completion = self.completion
      self.completion = nil
      finishing = false
      DispatchQueue.main.async { completion?(payload) }
    }
  }
}
