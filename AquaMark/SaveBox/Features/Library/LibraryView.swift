import SwiftUI

struct LibraryView: View {
    @EnvironmentObject var l10n: L10n
    @EnvironmentObject var engine: VideoDownloadEngine
    @State private var records: [DownloadRecord] = []

    var body: some View {
        NavigationStack {
            ZStack {
                DS.Colors.bg.ignoresSafeArea()

                if records.isEmpty {
                    emptyState
                } else {
                    recordsList
                }
            }
            .navigationTitle(l10n.libraryTitle)
            .navigationBarTitleDisplayMode(.large)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .onAppear { records = engine.loadRecords() }
        }
    }

    private var emptyState: some View {
        VStack(spacing: DS.Spacing.lg) {
            ZStack {
                Circle()
                    .fill(DS.Colors.bgTertiary)
                    .frame(width: 80, height: 80)
                Image(systemName: "arrow.down.doc")
                    .font(.system(size: 32, weight: .medium))
                    .foregroundColor(DS.Colors.textMuted)
            }

            Text(l10n.libraryEmpty)
                .font(DS.Fonts.title2)
                .foregroundColor(DS.Colors.textSecondary)

            Text(l10n.libraryEmptyHint)
                .font(DS.Fonts.callout)
                .foregroundColor(DS.Colors.textMuted)
                .multilineTextAlignment(.center)
        }
        .padding(.horizontal, 40)
    }

    private var recordsList: some View {
        List {
            ForEach(records) { record in
                HStack(spacing: DS.Spacing.md) {
                    ZStack {
                        RoundedRectangle(cornerRadius: DS.Radius.sm)
                            .fill(Color(hex: record.platform.color).opacity(0.12))
                            .frame(width: 48, height: 48)
                        Image(systemName: record.platform.icon)
                            .font(.system(size: 18, weight: .medium))
                            .foregroundColor(Color(hex: record.platform.color))
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text(record.title)
                            .font(DS.Fonts.headline)
                            .foregroundColor(DS.Colors.textPrimary)
                            .lineLimit(1)

                        HStack(spacing: 6) {
                            Text(record.platform.rawValue)
                                .font(DS.Fonts.caption)
                                .foregroundColor(Color(hex: record.platform.color))
                            Text("·")
                                .foregroundColor(DS.Colors.textMuted)
                            Text(record.quality)
                                .font(DS.Fonts.caption)
                                .foregroundColor(DS.Colors.textMuted)
                            Text("·")
                                .foregroundColor(DS.Colors.textMuted)
                            Text(record.timeAgo)
                                .font(DS.Fonts.caption)
                                .foregroundColor(DS.Colors.textMuted)
                        }
                    }

                    Spacer()

                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 18))
                        .foregroundColor(DS.Colors.success)
                }
                .padding(.vertical, 4)
                .listRowBackground(DS.Colors.card)
            }
            .onDelete { indexSet in
                records.remove(atOffsets: indexSet)
                if let data = try? JSONEncoder().encode(records) {
                    UserDefaults.standard.set(data, forKey: "download_records")
                }
            }
        }
        .scrollContentBackground(.hidden)
        .background(DS.Colors.bg)
    }
}
