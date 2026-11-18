# First iPhone development build

Goal: build and install the existing Silent Voice mobile app on Andrei's iPhone, with bundled JavaScript and no recognition runtime.

## Decisions

- Use Expo SDK 57 and the existing dependency versions and single root lockfile.
- Use the development identifier `br.com.silentvoice.mobile.dev`.
- Build locally in Release configuration, using the existing Apple Development identity and Personal Team. Keep signing metadata and native output local and ignored by Git.
- Preserve authentication, routes, UI and demonstration behavior. R4, camera capture, private artifacts and the handoff fixtures are outside this build.
- Preserve `main`; work on `codex/ios-device-build` based on current `origin/main`. No commit, push or publication.

## Execution

- [x] Verify the connected iPhone, Developer Mode, compatible developer disk image, CocoaPods and signing identity.
- [x] Run the existing mobile tests: 29 passed before changes.
- [x] Configure the iOS bundle identifier.
- [x] Generate the ignored iOS project without npm installation or dependency upgrades.
- [x] Install its CocoaPods dependencies and inspect signing/capabilities.
- [x] Compile Release, provision and install on the connected physical iPhone.
- [x] Verify installation, launch and visible initial UI; distinguish installation, launch and app-flow checks in the report.
- [x] Run repository checks appropriate to the configuration change and inspect the final diff.

## Acceptance and limits

A signed build is installed and opens on the physical iPhone without a Metro server. Authentication and the current flows are preserved. No claim of recognition, hardware integration or offline first login is made.

Record actual build failures and their smallest scoped fixes here. Never bypass certificate validation, change signing trust, alter production services or add private material to Git.

## Results

The generated target has no additional entitlements. CocoaPods installed 103 pods. Root tests, typecheck, web/API build and mobile lint/types/format passed. Expo Doctor passed 20/21 checks; its only failure is the six pre-existing Expo patch-version mismatches, which remain unchanged. The explicit dependency check reports the same mismatches.

Prebuild also changed the existing Android/iOS npm scripts; these automatic edits were reverted to preserve their behavior. Mobile lint and formatting now exclude ignored generated `ios/` and `android/` output.

Native compilation, linking and JavaScript bundling reached the framework-signing stage. The first attempt was cancelled at the operator's request because five parallel `codesign` processes opened overlapping keychain prompts. A second local Xcode build uses `COCOAPODS_PARALLEL_CODE_SIGN=false` to request one signature at a time. No keychain password, access policy or trust settings were changed for this retry.

Independent configuration review found no correctness issues.

The serial retry completed successfully (`BUILD SUCCEEDED`), with `codesign --verify --deep --strict` passing. The embedded profile has the expected team and application identifier and includes the connected iPhone. `main.jsbundle` is embedded in the Release app.

`devicectl device install app` confirmed installation of `br.com.silentvoice.mobile.dev`. The first launch was denied by iOS with a security error mentioning signature, entitlements or an untrusted profile. Local signature and provisioning checks passed. After the operator trusted the developer on the iPhone, `devicectl device process launch` succeeded and a subsequent process query confirmed `SilentVoice` remained running (PID 869).

The operator confirmed the welcome/login screen was visible on the physical iPhone. Device Hub screen mirroring remained at "Connecting display", so visible UI acceptance is operator-confirmed. No login submission or authenticated app flows were tested. The Release app embeds JavaScript and was launched without a Metro server. No camera or R4 inference was added or tested.

The development profile expires at 2026-11-06 01:42:19 UTC. Build/install/launch logs are local under `/tmp/silent-voice-ios-*-20261029.*`; no commit, push or publication was performed.
