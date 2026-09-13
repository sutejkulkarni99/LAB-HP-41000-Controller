pragma Singleton
import QtQuick

QtObject {
    property bool isDark: (typeof themeBridge !== "undefined") ? themeBridge.isDark : true

    readonly property color bg: isDark ? "#05070E" : "#F8FAFC"
    readonly property color card: isDark ? "#0E1220" : "#FFFFFF"
    readonly property color cardHover: isDark ? "#121828" : "#F1F5F9"
    readonly property color border: isDark ? "#1B2238" : "#E2E8F0"
    readonly property color text: isDark ? "#E8ECF5" : "#0F172A"
    readonly property color muted: isDark ? "#8B94AD" : "#475569"
    readonly property color accent: isDark ? "#7DD3FC" : "#0284C7"
    readonly property color brand: isDark ? "#F5E6C8" : "#0F172A"
    readonly property color ok: "#4ADE80"
    readonly property color warn: "#FBBF24"
    readonly property color err: "#F87171"

    readonly property int fontSizeTitle: 18
    readonly property int fontSizeBody: 13
    readonly property int fontSizeSmall: 11
    readonly property int radiusSm: 4
    readonly property int radiusMd: 8
    readonly property int radiusLg: 14
}

