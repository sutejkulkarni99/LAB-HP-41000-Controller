import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "components"

ApplicationWindow {
    id: window
    width: 1400
    height: 900
    minimumWidth: 1024
    minimumHeight: 700
    visible: true
    title: "Lab Bench Orchestrator v7"
    color: Theme.bg

    property int activeMode: 0 // 0: Bench, 1: Protocol, 2: Archive

    Column {
        anchors.fill: parent

        // Main Navigation & Header Bar
        Rectangle {
            width: parent.width
            height: 56
            color: Theme.card
            border.color: Theme.border
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                spacing: 24

                // App Brand
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10

                    Rectangle {
                        width: 24
                        height: 24
                        radius: 6
                        color: Theme.accent
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "V7"
                            color: Theme.card
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    Text {
                        text: "LAB BENCH ORCHESTRATOR"
                        color: Theme.text
                        font.pixelSize: 15
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Rectangle { width: 1; height: 26; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }

                // Mode Selectors (Bench, Protocol, Archive)
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8

                    Button {
                        text: "BENCH (LIVE)"
                        highlighted: window.activeMode === 0
                        onClicked: window.activeMode = 0
                    }

                    Button {
                        text: "PROTOCOL (YAML)"
                        highlighted: window.activeMode === 1
                        onClicked: window.activeMode = 1
                    }

                    Button {
                        text: "ARCHIVE (ANALYSIS)"
                        highlighted: window.activeMode === 2
                        onClicked: window.activeMode = 2
                    }
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                // Theme Toggle
                Button {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Theme.isDark ? "☀ LIGHT" : "🌙 DARK"
                    onClicked: themeBridge.toggleTheme()
                }
            }
        }

        // Active View Container
        Item {
            width: parent.width
            height: parent.height - 56

            BenchView {
                anchors.fill: parent
                visible: window.activeMode === 0
            }

            ProtocolView {
                anchors.fill: parent
                visible: window.activeMode === 1
            }

            ArchiveView {
                anchors.fill: parent
                visible: window.activeMode === 2
            }
        }
    }
}
