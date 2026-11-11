// swift-tools-version: 5.9
import PackageDescription

let package = Package(
  name: "SilentVoiceCaptureCore",
  platforms: [.macOS(.v13), .iOS(.v16)],
  targets: [
    .target(name: "CaptureCore", path: "ios", exclude: ["CaptureController.swift", "CapturePreviewView.swift", "SilentVoiceCaptureModule.swift", "SilentVoiceCapture.podspec"], sources: ["CaptureTimeline.swift", "BGR8Converter.swift", "CapturePosture.swift"]),
    .testTarget(name: "CaptureCoreTests", dependencies: ["CaptureCore"], path: "Tests")
  ]
)
