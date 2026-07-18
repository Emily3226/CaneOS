import Foundation
import WatchConnectivity
import WatchKit
internal import Combine

final class WatchSessionManager: NSObject, ObservableObject, WCSessionDelegate {
    static let shared = WatchSessionManager()

    @Published var lastDirection: String = "-"
    @Published var isPhoneReachable: Bool = false
    @Published var sosActive: Bool = false

    @Published var hapticIntensity: String = "medium" {
        didSet { UserDefaults.standard.set(hapticIntensity, forKey: "watchHapticIntensity") }
    }
    @Published var audioEnabled: Bool = true {
        didSet { UserDefaults.standard.set(audioEnabled, forKey: "watchAudioEnabled") }
    }

    private override init() {
        hapticIntensity = UserDefaults.standard.string(forKey: "watchHapticIntensity") ?? "medium"
        audioEnabled    = UserDefaults.standard.object(forKey: "watchAudioEnabled") as? Bool ?? true
        super.init()
        if WCSession.isSupported() {
            WCSession.default.delegate = self
            WCSession.default.activate()
        }
    }

    // MARK: - Public actions

    func requestScan() {
        let msg: [String: Any] = ["command": "scan_now"]
        if WCSession.default.isReachable {
            WCSession.default.sendMessage(msg, replyHandler: nil)
        }
        WKInterfaceDevice.current().play(.click)
    }

    func cancelSOS() {
        sosActive = false
        let msg: [String: Any] = ["type": "sos_cancel"]
        if WCSession.default.isReachable {
            WCSession.default.sendMessage(msg, replyHandler: nil)
        } else {
            WCSession.default.transferUserInfo(msg)
        }
    }

    func dismissSOSOverlay() {
        sosActive = false
    }

    // MARK: - Incoming message routing

    func session(_ session: WCSession, didReceiveMessage message: [String: Any]) {
        handle(message)
    }

    func session(_ session: WCSession, didReceiveUserInfo userInfo: [String: Any]) {
        handle(userInfo)
    }

    private func handle(_ message: [String: Any]) {
        DispatchQueue.main.async {
            if let type = message["type"] as? String {
                switch type {
                case "sos_alert":
                    if message["active"] as? Bool == true {
                        self.sosActive = true
                        WKInterfaceDevice.current().play(.failure)
                    }
                case "sos_clear":
                    self.sosActive = false
                default:
                    break
                }
            }
            if let direction = message["direction"] as? String {
                // The phone's intensity setting rides along with each buzz;
                // adopt it so the Watch always matches the phone app.
                if let intensity = message["intensity"] as? String {
                    self.hapticIntensity = intensity
                }
                self.lastDirection = direction
                self.playHaptic(for: direction)
            }
        }
    }

    /// Settings mirrored from the phone (fire-and-forget, latest value wins).
    func session(_ session: WCSession, didReceiveApplicationContext applicationContext: [String: Any]) {
        DispatchQueue.main.async {
            if let intensity = applicationContext["hapticIntensity"] as? String {
                self.hapticIntensity = intensity
            }
        }
    }

    // Apple Watch only exposes preset haptic types — no custom spatial
    // patterns, and no amplitude control. The navigation haptics
    // (.navigationLeftTurn/RightTurn) turned out not to produce a feelable
    // buzz outside an active navigation session, so each direction maps to
    // one of the strong, always-available presets instead:
    //   left  → .directionDown  (falling two-tone)
    //   right → .success        (rising "da-DUM")
    //   up    → .directionUp    (rising two-tone)
    // Perceived strength comes from repeating the pattern: the intensity
    // setting from the phone app picks the repeat count.
    private func playHaptic(for direction: String) {
        let device = WKInterfaceDevice.current()

        let haptic: WKHapticType
        switch direction {
        case "left":  haptic = .directionDown
        case "right": haptic = .success
        case "up":    haptic = .directionUp
        default:
            // /ws/haptics only ever sends left/right/up -- anything else here
            // means a malformed message got through, not a valid 4th sensor.
            if hapticIntensity != "low" { device.play(.click) }
            return
        }

        let repeats: Int
        switch hapticIntensity {
        case "low":  repeats = 1
        case "high": repeats = 5
        default:     repeats = 3
        }

        for i in 0..<repeats {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(i) * 0.30) {
                device.play(haptic)
            }
        }
    }

    // MARK: - WCSessionDelegate

    func session(_ session: WCSession, activationDidCompleteWith state: WCSessionActivationState, error: Error?) {}

    func sessionReachabilityDidChange(_ session: WCSession) {
        DispatchQueue.main.async { self.isPhoneReachable = session.isReachable }
    }
}