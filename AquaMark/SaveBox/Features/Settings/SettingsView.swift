import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var l10n: L10n
    @EnvironmentObject var engine: VideoDownloadEngine
    @AppStorage("auto_save_photos") private var autoSave = true
    @AppStorage("download_quality") private var quality = "1080"
    @State private var showLanguagePicker = false

    var body: some View {
        NavigationStack {
            ZStack {
                DS.Colors.bg.ignoresSafeArea()

                List {
                    // Language
                    Section {
                        Button {
                            showLanguagePicker = true
                        } label: {
                            HStack {
                                Label {
                                    Text(l10n.settingsLanguage)
                                        .foregroundColor(DS.Colors.textPrimary)
                                } icon: {
                                    Image(systemName: "globe")
                                        .foregroundColor(DS.Colors.secondary)
                                }
                                Spacer()
                                Text("\(l10n.lang.flag) \(l10n.lang.rawValue)")
                                    .font(DS.Fonts.callout)
                                    .foregroundColor(DS.Colors.textMuted)
                                Image(systemName: "chevron.right")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(DS.Colors.textMuted)
                            }
                        }
                        .listRowBackground(DS.Colors.card)
                    }

                    // Download settings
                    Section {
                        // Quality picker
                        HStack {
                            Label {
                                Text(l10n.settingsQuality)
                                    .foregroundColor(DS.Colors.textPrimary)
                            } icon: {
                                Image(systemName: "sparkles")
                                    .foregroundColor(DS.Colors.accent)
                            }
                            Spacer()
                            Picker("", selection: $quality) {
                                Text("Best").tag("best")
                                Text("1080p").tag("1080")
                                Text("720p").tag("720")
                                Text("480p").tag("480")
                            }
                            .tint(DS.Colors.accent)
                        }
                        .listRowBackground(DS.Colors.card)

                        // Auto save toggle
                        Toggle(isOn: $autoSave) {
                            Label {
                                Text(l10n.settingsAutoSave)
                                    .foregroundColor(DS.Colors.textPrimary)
                            } icon: {
                                Image(systemName: "photo.on.rectangle")
                                    .foregroundColor(DS.Colors.success)
                            }
                        }
                        .tint(DS.Colors.accent)
                        .listRowBackground(DS.Colors.card)
                    }

                    // Diagnostics
                    Section {
                        NavigationLink {
                            SelfCheckView()
                        } label: {
                            Label {
                                Text("System Check")
                                    .foregroundColor(DS.Colors.textPrimary)
                            } icon: {
                                Image(systemName: "checkmark.shield")
                                    .foregroundColor(DS.Colors.warning)
                            }
                        }
                        .listRowBackground(DS.Colors.card)
                    }

                    // About
                    Section {
                        HStack {
                            Label {
                                Text(l10n.settingsAbout)
                                    .foregroundColor(DS.Colors.textPrimary)
                            } icon: {
                                Image(systemName: "info.circle")
                                    .foregroundColor(DS.Colors.info)
                            }
                            Spacer()
                            Text("v1.0.0")
                                .font(DS.Fonts.caption)
                                .foregroundColor(DS.Colors.textMuted)
                        }
                        .listRowBackground(DS.Colors.card)

                        Button {
                            engine.clearRecords()
                        } label: {
                            Label {
                                Text("Clear Download History")
                                    .foregroundColor(DS.Colors.error)
                            } icon: {
                                Image(systemName: "trash")
                                    .foregroundColor(DS.Colors.error)
                            }
                        }
                        .listRowBackground(DS.Colors.card)
                    }
                }
                .scrollContentBackground(.hidden)
            }
            .navigationTitle(l10n.settingsTitle)
            .navigationBarTitleDisplayMode(.large)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .sheet(isPresented: $showLanguagePicker) {
                LanguagePickerView()
            }
        }
    }
}

struct LanguagePickerView: View {
    @EnvironmentObject var l10n: L10n
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationStack {
            List(AppLanguage.allCases) { language in
                Button {
                    l10n.lang = language
                    dismiss()
                } label: {
                    HStack(spacing: DS.Spacing.md) {
                        Text(language.flag)
                            .font(.system(size: 28))

                        Text(language.rawValue)
                            .font(DS.Fonts.headline)
                            .foregroundColor(DS.Colors.textPrimary)

                        Spacer()

                        if l10n.lang == language {
                            Image(systemName: "checkmark.circle.fill")
                                .font(.system(size: 20))
                                .foregroundColor(DS.Colors.accent)
                        }
                    }
                    .padding(.vertical, 4)
                }
                .listRowBackground(DS.Colors.card)
            }
            .scrollContentBackground(.hidden)
            .background(DS.Colors.bg)
            .navigationTitle("Language")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundColor(DS.Colors.accent)
                }
            }
        }
    }
}
