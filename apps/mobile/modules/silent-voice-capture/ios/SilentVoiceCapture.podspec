Pod::Spec.new do |s|
  s.name = 'SilentVoiceCapture'
  s.version = '0.1.0'
  s.summary = 'Internal front-camera acquisition diagnostics for Silent Voice'
  s.description = s.summary
  s.license = { :type => 'Proprietary' }
  s.author = 'Silent Voice'
  s.homepage = 'https://github.com/andreiolicar/silent-voice'
  s.source = { :git => 'https://github.com/andreiolicar/silent-voice.git' }
  s.platform = :ios, '16.4'
  s.swift_version = '5.9'
  s.static_framework = true
  s.dependency 'ExpoModulesCore'
  s.source_files = '*.swift'
  s.frameworks = 'AVFoundation', 'UIKit', 'CoreMedia', 'CoreVideo'
  s.pod_target_xcconfig = { 'DEFINES_MODULE' => 'YES' }
end
