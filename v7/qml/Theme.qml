pragma Singleton
import QtQuick

QtObject {
    property bool isDark: (typeof themeBridge !== "undefined") ? themeBridge.isDark : true

    readonly property color bg: isDark ? "#05070E" : "#F8FAFC"
    readonly property color card: isDark ? "#0E1220" : "#FFFFFF"
    readonly property color cardHover: isDark ? "#141A2E" : "#F1F5F9"
    readonly property color border: isDark ? "#1B2238" : "#E2E8F0"
    readonly property color text: isDark ? "#E8ECF5" : "#0F172A"
    readonly property color muted: isDark ? "#8B94AD" : "#64748B"
    readonly property color accent: isDark ? "#7DD3FC" : "#0284C7"
    readonly property color brand: isDark ? "#F5E6C8" : "#D97706"
    readonly property color ok: isDark ? "#4ADE80" : "#16A34A"
    readonly property color warn: isDark ? "#FBBF24" : "#D97706"
    readonly property color err: isDark ? "#F87171" : "#DC2626"
}
