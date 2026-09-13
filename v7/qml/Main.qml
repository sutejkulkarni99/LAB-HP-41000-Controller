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
    property bool psuConnected: false
    property bool rtbConnected: false
    property bool tekConnected: false
    property bool genConnected: false

    Connections {
        target: instrumentsBridge
        function onInstrumentConnected(shortId) {
            if (shortId === "labhp_41000") window.psuConnected = true;
            else if (shortId === "rtb2000") window.rtbConnected = true;
            else if (shortId === "mso2004b") window.tekConnected = true;
            else if (shortId === "fg_edu33212a") window.genConnected = true;
        }
        function onInstrumentDisconnected(shortId) {
            if (shortId === "labhp_41000") window.psuConnected = false;
            else if (shortId === "rtb2000") window.rtbConnected = false;
            else if (shortId === "mso2004b") window.tekConnected = false;
            else if (shortId === "fg_edu33212a") window.genConnected = false;
        }
    }

    Column {
        anchors.fill: parent

        // Main Navigation & Header Bar (Canonical Top Bar)
        Rectangle {
            width: parent.width
            height: 52
            color: Theme.card
            border.color: Theme.border
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12

                // Connection chips (● PSU, ● R&S, ● Tek) - same position always
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6

                    ConnectionChip {
                        instrumentId: "labhp_41000"
                        title: "PSU"
                        defaultResource: "192.168.1.100:10001"
                        connected: window.psuConnected
                    }

                    ConnectionChip {
                        instrumentId: "rtb2000"
                        title: "R&S"
                        defaultResource: "192.168.1.101:5025"
                        connected: window.rtbConnected
                    }

                    ConnectionChip {
                        instrumentId: "mso2004b"
                        title: "Tek"
                        defaultResource: "192.168.1.102:5025"
                        connected: window.tekConnected
                    }
                }

                Rectangle { width: 1; height: 24; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }

                // Mode Selectors (BENCH top-left corner)
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6

                    Button {
                        height: 32
                        text: "BENCH"
                        highlighted: window.activeMode === 0
                        onClicked: window.activeMode = 0
                    }

                    Button {
                        height: 32
                        text: "PROTOCOL"
                        highlighted: window.activeMode === 1
                        onClicked: window.activeMode = 1
                    }

                    Button {
                        height: 32
                        text: "ARCHIVE"
                        highlighted: window.activeMode === 2
                        onClicked: window.activeMode = 2
                    }
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                // Theme Toggle (☀/☾)
                Button {
                    height: 32
                    anchors.verticalCenter: parent.verticalCenter
                    text: Theme.isDark ? "☀" : "☾"
                    onClicked: themeBridge.toggleTheme()
                }

                // Menu ☰ (Toggles Inspector Drawer)
                Button {
                    id: menuBtn
                    height: 32
                    anchors.verticalCenter: parent.verticalCenter
                    text: "☰"
                    onClicked: inspectorDrawer.open = !inspectorDrawer.open
                }

                // E-STOP (Far right, always visible)
                EStopButton {
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // Active View Container
        Item {
            width: parent.width
            height: parent.height - 52

            BenchView {
                id: benchView
                anchors.fill: parent
                visible: window.activeMode === 0
                onInspectorRequested: function(instId) {
                    inspectorDrawer.activeInstrumentId = instId;
                    inspectorDrawer.open = true;
                }
            }

            ProtocolView {
                anchors.fill: parent
                visible: window.activeMode === 1
            }

            ArchiveView {
                anchors.fill: parent
                visible: window.activeMode === 2
            }

            // Global Inspector Drawer accessible across the app
            InspectorDrawer {
                id: inspectorDrawer
            }
        }
    }
}
