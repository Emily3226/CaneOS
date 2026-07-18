import SwiftUI

struct ContentView: View {
    @StateObject private var session = WatchSessionManager.shared
    @State private var pulse = false

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: "figure.walk")
                .font(.largeTitle)
            Text("Cane Companion")
                .font(.headline)

            HStack(spacing: 6) {
                Circle()
                    .fill(Color.green)
                    .frame(width: 10, height: 10)
                    .scaleEffect(pulse ? 1.4 : 1.0)
                    .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: pulse)
                Text("LIVE ON WATCH")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(.green)
            }
            .onAppear { pulse = true }

            Text("Last: \(session.lastDirection)")
                .font(.footnote)
                .foregroundColor(.secondary)
        }
        .padding()
    }
}
