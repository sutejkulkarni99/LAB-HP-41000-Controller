import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    width: parent.width
    height: 48
    color: Theme.card
    border.color: Theme.border
    border.width: 1

    Row {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 20

        // Session Action Buttons
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            Button {
                height: 32
                text: "⏵ START"
                enabled: !sessionBridge.running
                onClicked: {
                    var confs = [
                        {"short_id": "labhp_41000", "interval_s": 0.1},
                        {"short_id": "rtb2000", "interval_s": 0.1},
                        {"short_id": "mso2004b", "interval_s": 0.1}
                    ];
                    sessionBridge.startSession("", confs);
                }
            }

            Button {
                height: 32
                text: sessionBridge.paused ? "RESUME" : "⏸ PAUSE"
                enabled: sessionBridge.running
                onClicked: {
                    if (sessionBridge.paused) {
                        sessionBridge.resumeSession();
                    } else {
                        sessionBridge.pauseSession();
                    }
                }
            }

            Button {
                height: 32
                text: "⏹ STOP"
                enabled: sessionBridge.running
                onClicked: sessionBridge.stopSession()
            }
        }

        Rectangle { width: 1; height: 24; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }

        // Clock Status
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10

            Rectangle {
                width: 8
                height: 8
                radius: 4
                anchors.verticalCenter: parent.verticalCenter
                color: sessionBridge.running ? (sessionBridge.paused ? Theme.warn : Theme.ok) : Theme.muted
            }

            Text {
                text: "Clock: " + sessionBridge.clockLabel
                color: Theme.text
                font.pixelSize: 13
                font.bold: true
                font.family: "Monospace"
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Item { width: 1; height: 1; Layout.fillWidth: true }

        // Row Counters (LOGGED: 0 until session runs, then PSU: X  R&S: Y  Tek: Z)
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            Text {
                text: {
                    if (!sessionBridge.running) {
                        return "LOGGED: 0";
                    }
                    var counts = sessionBridge.rowCounts;
                    var psu = counts["labhp_41000"] || 0;
                    var rtb = counts["rtb2000"] || 0;
                    var tek = counts["mso2004b"] || 0;
                    return "PSU: " + psu + "  R&S: " + rtb + "  Tek: " + tek;
                }
                color: Theme.accent
                font.pixelSize: 12
                font.bold: true
                font.family: "Monospace"
            }
        }
    }
}

