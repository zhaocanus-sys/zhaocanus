import SwiftUI

struct SelfCheckView: View {
    @StateObject private var checker = SelfCheckService()

    var body: some View {
        ZStack {
            DS.Colors.bg.ignoresSafeArea()

            List {
                Section {
                    if checker.isRunning {
                        HStack {
                            ProgressView().tint(DS.Colors.accent)
                            Text("Running checks...")
                                .font(DS.Fonts.callout)
                                .foregroundColor(DS.Colors.textSecondary)
                                .padding(.leading, 8)
                        }
                        .listRowBackground(DS.Colors.card)
                    } else if checker.results.isEmpty {
                        Button {
                            Task { await checker.runAllChecks() }
                        } label: {
                            HStack {
                                Image(systemName: "play.circle.fill")
                                    .font(.system(size: 20))
                                    .foregroundColor(DS.Colors.accent)
                                Text("Run System Check")
                                    .font(DS.Fonts.headline)
                                    .foregroundColor(DS.Colors.accent)
                            }
                        }
                        .listRowBackground(DS.Colors.card)
                    } else {
                        let passed = checker.results.filter(\.passed).count
                        let total = checker.results.count
                        HStack {
                            Image(systemName: passed == total ? "checkmark.shield.fill" : "exclamationmark.shield.fill")
                                .font(.system(size: 24))
                                .foregroundColor(passed == total ? DS.Colors.success : DS.Colors.warning)
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(passed)/\(total) checks passed")
                                    .font(DS.Fonts.headline)
                                    .foregroundColor(DS.Colors.textPrimary)
                                Text(passed == total ? "All systems operational" : "Some issues found")
                                    .font(DS.Fonts.caption)
                                    .foregroundColor(DS.Colors.textMuted)
                            }
                        }
                        .listRowBackground(DS.Colors.card)
                    }
                }

                if !checker.results.isEmpty {
                    Section("Results") {
                        ForEach(checker.results) { result in
                            HStack(spacing: DS.Spacing.md) {
                                Image(systemName: result.passed ? "checkmark.circle.fill" : "xmark.circle.fill")
                                    .font(.system(size: 18))
                                    .foregroundColor(result.passed ? DS.Colors.success : DS.Colors.error)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text(result.name)
                                        .font(DS.Fonts.headline)
                                        .foregroundColor(DS.Colors.textPrimary)
                                    Text(result.detail)
                                        .font(DS.Fonts.caption)
                                        .foregroundColor(DS.Colors.textMuted)
                                }
                            }
                            .listRowBackground(DS.Colors.card)
                        }
                    }

                    Section {
                        Button {
                            Task { await checker.runAllChecks() }
                        } label: {
                            HStack {
                                Image(systemName: "arrow.clockwise")
                                Text("Run Again")
                            }
                            .font(DS.Fonts.headline)
                            .foregroundColor(DS.Colors.accent)
                        }
                        .listRowBackground(DS.Colors.card)
                    }
                }
            }
            .scrollContentBackground(.hidden)
        }
        .navigationTitle("System Check")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if checker.results.isEmpty {
                Task { await checker.runAllChecks() }
            }
        }
    }
}
