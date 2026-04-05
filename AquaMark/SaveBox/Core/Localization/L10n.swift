import SwiftUI

enum AppLanguage: String, CaseIterable, Identifiable {
    case en = "English"
    case zh = "中文"
    case es = "Español"
    case ar = "العربية"
    case pt = "Português"
    case ru = "Русский"
    case ja = "日本語"
    case ko = "한국어"
    case fr = "Français"
    case de = "Deutsch"

    var id: String { rawValue }

    var code: String {
        switch self {
        case .en: return "en"
        case .zh: return "zh"
        case .es: return "es"
        case .ar: return "ar"
        case .pt: return "pt"
        case .ru: return "ru"
        case .ja: return "ja"
        case .ko: return "ko"
        case .fr: return "fr"
        case .de: return "de"
        }
    }

    var flag: String {
        switch self {
        case .en: return "🇺🇸"
        case .zh: return "🇨🇳"
        case .es: return "🇪🇸"
        case .ar: return "🇸🇦"
        case .pt: return "🇧🇷"
        case .ru: return "🇷🇺"
        case .ja: return "🇯🇵"
        case .ko: return "🇰🇷"
        case .fr: return "🇫🇷"
        case .de: return "🇩🇪"
        }
    }
}

class L10n: ObservableObject {
    @Published var lang: AppLanguage {
        didSet { UserDefaults.standard.set(lang.code, forKey: "app_language") }
    }

    init() {
        let saved = UserDefaults.standard.string(forKey: "app_language") ?? "en"
        self.lang = AppLanguage.allCases.first(where: { $0.code == saved }) ?? .en
    }

    // --- Tabs ---
    var tabHome: String { t("Home", "首页", "Inicio", "الرئيسية", "Início", "Главная", "ホーム", "홈", "Accueil", "Startseite") }
    var tabLibrary: String { t("Library", "媒体库", "Biblioteca", "المكتبة", "Biblioteca", "Медиатека", "ライブラリ", "라이브러리", "Bibliothèque", "Mediathek") }
    var tabSettings: String { t("Settings", "设置", "Ajustes", "الإعدادات", "Configurações", "Настройки", "設定", "설정", "Paramètres", "Einstellungen") }

    // --- Home ---
    var homeTitle: String { t("SaveBox", "SaveBox", "SaveBox", "SaveBox", "SaveBox", "SaveBox", "SaveBox", "SaveBox", "SaveBox", "SaveBox") }
    var homeSubtitle: String { t("Download any video, anywhere", "下载任何视频", "Descarga cualquier vídeo", "حمّل أي فيديو", "Baixe qualquer vídeo", "Скачать любое видео", "どんな動画もダウンロード", "모든 비디오 다운로드", "Téléchargez n'importe quelle vidéo", "Jedes Video herunterladen") }
    var homePaste: String { t("Paste link here...", "粘贴链接...", "Pegar enlace...", "الصق الرابط...", "Colar link...", "Вставьте ссылку...", "リンクを貼り付け...", "링크를 붙여넣기...", "Coller le lien...", "Link einfügen...") }
    var homeDownload: String { t("Download", "下载", "Descargar", "تحميل", "Baixar", "Скачать", "ダウンロード", "다운로드", "Télécharger", "Herunterladen") }
    var homePasteClipboard: String { t("Paste", "粘贴", "Pegar", "لصق", "Colar", "Вставить", "貼付", "붙여넣기", "Coller", "Einfügen") }
    var homeSupported: String { t("Supported Platforms", "支持的平台", "Plataformas soportadas", "المنصات المدعومة", "Plataformas suportadas", "Поддерживаемые платформы", "対応プラットフォーム", "지원 플랫폼", "Plateformes prises en charge", "Unterstützte Plattformen") }

    // --- Download ---
    var downloadFetching: String { t("Fetching video info...", "获取视频信息...", "Obteniendo información...", "جاري جلب المعلومات...", "Obtendo informações...", "Получение информации...", "動画情報を取得中...", "비디오 정보 가져오는 중...", "Récupération des infos...", "Video-Info wird abgerufen...") }
    var downloadReady: String { t("Ready to download", "准备下载", "Listo para descargar", "جاهز للتحميل", "Pronto para baixar", "Готово к скачиванию", "ダウンロード準備完了", "다운로드 준비 완료", "Prêt à télécharger", "Bereit zum Herunterladen") }
    var downloadSaved: String { t("Saved to Photos!", "已保存到相册!", "¡Guardado en Fotos!", "تم الحفظ في الصور!", "Salvo nas Fotos!", "Сохранено в Фото!", "写真に保存しました!", "사진에 저장됨!", "Enregistré dans Photos!", "In Fotos gespeichert!") }
    var downloadFailed: String { t("Download failed", "下载失败", "Error de descarga", "فشل التحميل", "Falha no download", "Ошибка загрузки", "ダウンロード失敗", "다운로드 실패", "Échec du téléchargement", "Download fehlgeschlagen") }
    var downloadProgress: String { t("Downloading...", "下载中...", "Descargando...", "جاري التحميل...", "Baixando...", "Скачивание...", "ダウンロード中...", "다운로드 중...", "Téléchargement...", "Wird heruntergeladen...") }

    // --- Quality ---
    var qualityBest: String { t("Best Quality", "最佳画质", "Mejor calidad", "أفضل جودة", "Melhor qualidade", "Лучшее качество", "最高画質", "최고 화질", "Meilleure qualité", "Beste Qualität") }
    var qualityHigh: String { t("High (1080p)", "高清 (1080p)", "Alta (1080p)", "عالية (1080p)", "Alta (1080p)", "Высокое (1080p)", "高画質 (1080p)", "고화질 (1080p)", "Haute (1080p)", "Hoch (1080p)") }
    var qualityMedium: String { t("Medium (720p)", "标清 (720p)", "Media (720p)", "متوسطة (720p)", "Média (720p)", "Среднее (720p)", "標準 (720p)", "표준 (720p)", "Moyenne (720p)", "Mittel (720p)") }

    // --- Library ---
    var libraryTitle: String { t("Downloads", "下载记录", "Descargas", "التنزيلات", "Downloads", "Загрузки", "ダウンロード", "다운로드", "Téléchargements", "Downloads") }
    var libraryEmpty: String { t("No downloads yet", "还没有下载", "Sin descargas aún", "لا توجد تنزيلات", "Nenhum download ainda", "Нет загрузок", "ダウンロードなし", "다운로드 없음", "Pas encore de téléchargement", "Noch keine Downloads") }
    var libraryEmptyHint: String { t("Paste a link to start downloading", "粘贴链接开始下载", "Pega un enlace para empezar", "الصق رابطاً للبدء", "Cole um link para começar", "Вставьте ссылку", "リンクを貼って開始", "링크를 붙여넣어 시작", "Collez un lien pour commencer", "Link einfügen zum Starten") }

    // --- Settings ---
    var settingsTitle: String { t("Settings", "设置", "Ajustes", "الإعدادات", "Configurações", "Настройки", "設定", "설정", "Paramètres", "Einstellungen") }
    var settingsLanguage: String { t("Language", "语言", "Idioma", "اللغة", "Idioma", "Язык", "言語", "언어", "Langue", "Sprache") }
    var settingsQuality: String { t("Download Quality", "下载画质", "Calidad de descarga", "جودة التحميل", "Qualidade do download", "Качество загрузки", "ダウンロード画質", "다운로드 화질", "Qualité de téléchargement", "Download-Qualität") }
    var settingsAutoSave: String { t("Auto save to Photos", "自动保存到相册", "Guardar automáticamente", "حفظ تلقائي في الصور", "Salvar automaticamente", "Авто-сохранение в Фото", "写真に自動保存", "사진에 자동 저장", "Enregistrement auto dans Photos", "Automatisch in Fotos speichern") }
    var settingsAbout: String { t("About SaveBox", "关于 SaveBox", "Acerca de SaveBox", "حول SaveBox", "Sobre o SaveBox", "О SaveBox", "SaveBoxについて", "SaveBox 정보", "À propos de SaveBox", "Über SaveBox") }

    // --- Helpers ---
    private func t(_ en: String, _ zh: String, _ es: String, _ ar: String, _ pt: String, _ ru: String, _ ja: String, _ ko: String, _ fr: String, _ de: String) -> String {
        switch lang {
        case .en: return en
        case .zh: return zh
        case .es: return es
        case .ar: return ar
        case .pt: return pt
        case .ru: return ru
        case .ja: return ja
        case .ko: return ko
        case .fr: return fr
        case .de: return de
        }
    }
}
