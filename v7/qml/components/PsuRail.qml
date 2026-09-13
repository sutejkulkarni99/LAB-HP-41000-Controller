import QtQuick
import QtQuick.Controls
import v7.qml 1.0
import ".."

Rectangle {
    id: root
    property string instrumentId: "labhp_41000"
    property bool connected: false
    property var voltage: undefined
    property var current: undefined
    property var power: undefined
    property var resistance: undefined
    property real voltageMeas: voltage !== undefined ? Number(voltage) : 0.0
    property real currentMeas: current !== undefined ? Number(current) : 0.0
    property real powerMeas: power !== undefined ? Number(power) : 0.0
    property real resistanceMeas: resistance !== undefined ? Number(resistance) : 0.0
    property bool outputOn: false

    // Focus mode properties for the other (shrunk) scope
    property string focusedScope: ""
    property string unfocusedTitle: ""
    property bool unfocusedConnected: false
    property bool unfocusedRunning: false
    property real unfocusedCh1Vrms: 0.0
    property real unfocusedCh1Freq: 0.0
    property real unfocusedCh2Vrms: 0.0
    property real unfocusedCh2Freq: 0.0

    signal restoreSplitRequested()

    width: 280
    color: Theme.card
    border.color: Theme.border
    border.width: 1
    radius: 8

    Flickable {
        anchors.fill: parent
        anchors.margins: 14
        contentWidth: parent.width - 28
        contentHeight: railCol.implicitHeight + 10
        clip: true

        Column {
            id: railCol
            width: parent.width
            spacing: 12

            // Header Row
            Row {
                width: parent.width
                spacing: 8

                Column {
                    spacing: 2
                    Text {
                        text: "PSU RAIL"
                        color: Theme.text
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: "ETPS LAB-HP 41000"
                        color: Theme.muted
                        font.pixelSize: 10
                        font.family: "Monospace"
                    }
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                Rectangle {
                    width: 78
                    height: 22
                    radius: 4
                    color: !root.connected ? Theme.muted : (root.outputOn ? Theme.ok : Theme.warn)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: !root.connected ? "OFFLINE" : (root.outputOn ? "OUT ON" : "STANDBY")
                        color: Theme.card
                        font.pixelSize: 9
                        font.bold: true
                    }
                }
            }

            Rectangle { width: parent.width; height: 1; color: Theme.border }

            // Live Telemetry Readouts (shows '--' when disconnected)
            Column {
                width: parent.width
                spacing: 8

                MetricCard {
                    width: parent.width
                    height: 58
                    label: "VOLTAGE"
                    value: (root.voltage === undefined || (root.voltage == 0 && !root.connected)) ? "--" : Number(root.voltage !== undefined ? root.voltage : root.voltageMeas).toFixed(2)
                    unit: "V"
                    accentColor: Theme.accent
                }

                MetricCard {
                    width: parent.width
                    height: 58
                    label: "CURRENT"
                    value: (root.current === undefined || (root.current == 0 && !root.connected)) ? "--" : Number(root.current !== undefined ? root.current : root.currentMeas).toFixed(3)
                    unit: "A"
                    accentColor: Theme.warn
                }

                MetricCard {
                    width: parent.width
                    height: 58
                    label: "POWER"
                    value: (root.power === undefined || (root.power == 0 && !root.connected)) ? "--" : Number(root.power !== undefined ? root.power : root.powerMeas).toFixed(1)
                    unit: "W"
                    accentColor: "#A78BFA"
                }

                MetricCard {
                    width: parent.width
                    height: 58
                    label: "RESISTANCE"
                    value: {
                        if (root.resistance === undefined || (root.resistance == 0 && !root.connected)) return "--";
                        var r = Number(root.resistance !== undefined ? root.resistance : root.resistanceMeas);
                        return (r > 9999) ? "OPEN" : r.toFixed(1);
                    }
                    unit: "Ω"
                    accentColor: Theme.ok
                }
            }

            Rectangle { width: parent.width; height: 1; color: Theme.border }

            // Setpoints & Controls
            Column {
                width: parent.width
                spacing: 8

                Text {
                    text: "SETPOINTS & CONTROL"
                    color: Theme.muted
                    font.pixelSize: 10
                    font.bold: true
                }

                // Set V
                Row {
                    width: parent.width
                    spacing: 6
                    Text {
                        text: "Set V"
                        color: Theme.text
                        font.pixelSize: 11
                        font.bold: true
                        width: 44
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    TextField {
                        id: vSetInput
                        width: 120
                        height: 28
                        text: "48.0"
                        color: Theme.text
                        font.pixelSize: 11
                        background: Rectangle { color: Theme.bg; border.color: Theme.border; radius: 4 }
                    }
                    Button {
                        height: 28
                        text: "SET"
                        enabled: root.connected
                        onClicked: instrumentsBridge.setPsuSetpoint("voltage", parseFloat(vSetInput.text))
                    }
                }

                // Set I
                Row {
                    width: parent.width
                    spacing: 6
                    Text {
                        text: "Set I"
                        color: Theme.text
                        font.pixelSize: 11
                        font.bold: true
                        width: 44
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    TextField {
                        id: iSetInput
                        width: 120
                        height: 28
                        text: "5.0"
                        color: Theme.text
                        font.pixelSize: 11
                        background: Rectangle { color: Theme.bg; border.color: Theme.border; radius: 4 }
                    }
                    Button {
                        height: 28
                        text: "SET"
                        enabled: root.connected
                        onClicked: instrumentsBridge.setPsuSetpoint("current", parseFloat(iSetInput.text))
                    }
                }

                // Set P
                Row {
                    width: parent.width
                    spacing: 6
                    Text {
                        text: "Set P"
                        color: Theme.text
                        font.pixelSize: 11
                        font.bold: true
                        width: 44
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    TextField {
                        id: pSetInput
                        width: 120
                        height: 28
                        text: "250.0"
                        color: Theme.text
                        font.pixelSize: 11
                        background: Rectangle { color: Theme.bg; border.color: Theme.border; radius: 4 }
                    }
                    Button {
                        height: 28
                        text: "SET"
                        enabled: root.connected
                        onClicked: instrumentsBridge.setPsuSetpoint("power", parseFloat(pSetInput.text))
                    }
                }

                // OUTPUT Toggle Button with status dot ●
                Rectangle {
                    width: parent.width
                    height: 38
                    radius: 6
                    color: !root.connected ? Theme.border : (root.outputOn ? Theme.err : Theme.ok)

                    Row {
                        anchors.centerIn: parent
                        spacing: 8

                        Rectangle {
                            width: 10
                            height: 10
                            radius: 5
                            color: root.connected ? (root.outputOn ? "#22C55E" : "#EAB308") : "#94A3B8"
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: root.outputOn ? "OUTPUT ON (CLICK TO STOP)" : "OUTPUT STANDBY (CLICK ON)"
                            color: Theme.card
                            font.pixelSize: 11
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        enabled: root.connected
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

            // Compact 4-Row Summary Card for the unfocused scope in Focus Mode
            Rectangle {
                visible: root.focusedScope !== ""
                width: parent.width
                height: 120
                radius: 6
                color: Theme.bg
                border.color: Theme.accent
                border.width: 1

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.restoreSplitRequested()
                }

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6

                    // Row 1: Title & Status
                    Row {
                        width: parent.width
                        spacing: 6
                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: root.unfocusedConnected ? Theme.ok : Theme.muted
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: root.unfocusedTitle
                            color: Theme.text
                            font.pixelSize: 11
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Item { width: 1; height: 1; Layout.fillWidth: true }
                        Text {
                            text: root.unfocusedConnected ? (root.unfocusedRunning ? "RUNNING" : "STOPPED") : "OFFLINE"
                            color: Theme.muted
                            font.pixelSize: 9
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    // Row 2: CH1
                    Row {
                        width: parent.width
                        spacing: 6
                        Text { text: "CH1:"; color: "#FACC15"; font.pixelSize: 10; font.bold: true }
                        Text {
                            text: root.unfocusedConnected ? (root.unfocusedCh1Vrms.toFixed(2) + " Vrms  " + root.unfocusedCh1Freq.toFixed(0) + " Hz") : "--"
                            color: Theme.text
                            font.pixelSize: 10
                            font.family: "Monospace"
                        }
                    }

                    // Row 3: CH2
                    Row {
                        width: parent.width
                        spacing: 6
                        Text { text: "CH2:"; color: "#38BDF8"; font.pixelSize: 10; font.bold: true }
                        Text {
                            text: root.unfocusedConnected ? (root.unfocusedCh2Vrms.toFixed(2) + " Vrms  " + root.unfocusedCh2Freq.toFixed(0) + " Hz") : "--"
                            color: Theme.text
                            font.pixelSize: 10
                            font.family: "Monospace"
                        }
                    }

                    // Row 4: Restore Split Prompt
                    Row {
                        width: parent.width
                        Text {
                            text: "CLICK TO RESTORE SPLIT ⤢"
                            color: Theme.accent
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }
                }
            }
        }
    }
}

