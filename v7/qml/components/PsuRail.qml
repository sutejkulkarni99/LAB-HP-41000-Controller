import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property string instrumentId: "labhp_41000"
    property bool connected: false
    property real voltageMeas: 0.0
    property real currentMeas: 0.0
    property real powerMeas: 0.0
    property real resistanceMeas: 0.0
    property bool outputOn: false

    width: parent.width
    height: 140
    color: Theme.card
    border.color: Theme.border
    border.width: 1
    radius: 8

    Row {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 20

        // Identification & Status Column
        Column {
            width: 160
            spacing: 8

            Text {
                text: "ETPS LAB-HP 41000"
                color: Theme.brand
                font.pixelSize: 14
                font.bold: true
            }

            Text {
                text: "DC Power Source"
                color: Theme.muted
                font.pixelSize: 11
            }

            Rectangle {
                width: 100
                height: 28
                radius: 4
                color: root.connected ? (root.outputOn ? Theme.ok : Theme.warn) : Theme.muted

                Text {
                    anchors.centerIn: parent
                    text: !root.connected ? "OFFLINE" : (root.outputOn ? "OUTPUT ON" : "STANDBY")
                    color: Theme.card
                    font.pixelSize: 11
                    font.bold: true
                }
            }
        }

        // Live Telemetry Readouts
        Row {
            spacing: 12
            MetricCard {
                label: "VOLTAGE READOUT"
                value: root.voltageMeas.toFixed(2)
                unit: "V"
                accentColor: Theme.accent
            }
            MetricCard {
                label: "CURRENT READOUT"
                value: root.currentMeas.toFixed(3)
                unit: "A"
                accentColor: Theme.warn
            }
            MetricCard {
                label: "ACTIVE POWER"
                value: root.powerMeas.toFixed(1)
                unit: "W"
                accentColor: "#A78BFA"
            }
            MetricCard {
                label: "EST. LOAD"
                value: (root.resistanceMeas > 9999) ? "OPEN" : root.resistanceMeas.toFixed(1)
                unit: "Ω"
                accentColor: Theme.ok
            }
        }

        // Setpoints & Controls
        Row {
            spacing: 16
            anchors.verticalCenter: parent.verticalCenter

            Column {
                spacing: 4
                Text { text: "SET VOLTAGE (V)"; color: Theme.muted; font.pixelSize: 10; font.bold: true }
                Row {
                    spacing: 4
                    TextField {
                        id: vSetInput
                        width: 70
                        height: 32
                        text: "48.0"
                        color: Theme.text
                        background: Rectangle { color: Theme.bg; border.color: Theme.border; radius: 4 }
                    }
                    Button {
                        height: 32
                        text: "SET"
                        onClicked: instrumentsBridge.setPsuSetpoint("voltage", parseFloat(vSetInput.text))
                    }
                }
            }

            Column {
                spacing: 4
                Text { text: "SET CURRENT (A)"; color: Theme.muted; font.pixelSize: 10; font.bold: true }
                Row {
                    spacing: 4
                    TextField {
                        id: iSetInput
                        width: 70
                        height: 32
                        text: "5.0"
                        color: Theme.text
                        background: Rectangle { color: Theme.bg; border.color: Theme.border; radius: 4 }
                    }
                    Button {
                        height: 32
                        text: "SET"
                        onClicked: instrumentsBridge.setPsuSetpoint("current", parseFloat(iSetInput.text))
                    }
                }
            }

            // Output Toggle Button
            Rectangle {
                width: 90
                height: 48
                radius: 6
                anchors.verticalCenter: parent.verticalCenter
                color: root.outputOn ? Theme.err : Theme.ok

                Text {
                    anchors.centerIn: parent
                    text: root.outputOn ? "OUTPUT\nOFF" : "OUTPUT\nON"
                    color: Theme.card
                    font.pixelSize: 11
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.outputOn) {
                            instrumentsBridge.sendRawCommand(root.instrumentId, "SB,S");
                        } else {
                            instrumentsBridge.sendRawCommand(root.instrumentId, "SB,R");
                        }
                    }
                }
            }
        }
    }
}
