import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property string instrumentId: "rtb2000"
    property string title: "Rohde & Schwarz RTB2000"
    property bool connected: false
    property bool running: true

    property real ch1Vrms: 0.0
    property real ch1Vpp: 0.0
    property real ch1Freq: 0.0
    property real ch2Vrms: 0.0
    property real ch2Vpp: 0.0
    property real ch2Freq: 0.0

    color: Theme.card
    border.color: Theme.border
    border.width: 1
    radius: 8

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        // Header Row
        Row {
            width: parent.width
            spacing: 12

            Text {
                text: root.title
                color: Theme.text
                font.pixelSize: 14
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            Rectangle {
                width: 60
                height: 24
                radius: 4
                color: root.running ? Theme.ok : Theme.warn
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: root.running ? "RUNNING" : "STOPPED"
                    color: Theme.card
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            Button {
                text: root.running ? "STOP" : "RUN"
                onClicked: {
                    root.running = !root.running;
                    instrumentsBridge.setScopeControl(root.instrumentId, "RUN", root.running);
                }
            }

            Button {
                text: "AUTOSCALE"
                onClicked: instrumentsBridge.sendRawCommand(root.instrumentId, ":AUT")
            }
        }

        // Scope Display
        ScopeScreen {
            width: parent.width
            height: parent.height - 110
            running: root.running
        }

        // Bottom Controls and Live Metrics Bar
        Row {
            width: parent.width
            spacing: 16

            Row {
                spacing: 6
                Text { text: "TIMEBASE:"; color: Theme.muted; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter }
                Button { text: "1ms"; onClicked: instrumentsBridge.setScopeControl(root.instrumentId, "TIMEBASE", 0.001) }
                Button { text: "5ms"; onClicked: instrumentsBridge.setScopeControl(root.instrumentId, "TIMEBASE", 0.005) }
                Button { text: "10ms"; onClicked: instrumentsBridge.setScopeControl(root.instrumentId, "TIMEBASE", 0.010) }
            }

            Rectangle { width: 1; height: 26; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }

            Row {
                spacing: 12
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    text: "CH1: " + root.ch1Vrms.toFixed(2) + " Vrms  |  " + root.ch1Vpp.toFixed(2) + " Vpp  |  " + root.ch1Freq.toFixed(1) + " Hz"
                    color: "#FACC15"
                    font.pixelSize: 11
                    font.family: "Monospace"
                }

                Text {
                    text: "CH2: " + root.ch2Vrms.toFixed(2) + " Vrms  |  " + root.ch2Vpp.toFixed(2) + " Vpp  |  " + root.ch2Freq.toFixed(1) + " Hz"
                    color: "#38BDF8"
                    font.pixelSize: 11
                    font.family: "Monospace"
                }
            }
        }
    }
}
