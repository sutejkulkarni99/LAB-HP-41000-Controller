import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    width: parent.width
    height: 52
    color: Theme.card
    border.color: Theme.border
    border.width: 1

    Row {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 16

        // Mode and Clock Status
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            Rectangle {
                width: 10
                height: 10
                radius: 5
                anchors.verticalCenter: parent.verticalCenter
                color: sessionBridge.running ? (sessionBridge.paused ? Theme.warn : Theme.ok) : Theme.muted
            }

            Text {
                text: sessionBridge.running ? (sessionBridge.paused ? "PAUSED" : "RECORDING") : "STANDBY"
                color: Theme.text
                font.pixelSize: 12
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: sessionBridge.clockLabel
                color: Theme.accent
                font.pixelSize: 15
                font.bold: true
                font.family: "Monospace"
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Rectangle { width: 1; height: 26; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }

        // Session Action Buttons
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            Button {
                text: "START SESSION"
                enabled: !sessionBridge.running
                onClicked: {
                    var confs = [
                        {"short_id": "labhp_41000", "interval_s": 0.1},
                        {"short_id": "rtb2000", "interval_s": 0.1}
                    ];
                    sessionBridge.startSession("", confs);
                }
            }

            Button {
                text: sessionBridge.paused ? "RESUME" : "PAUSE"
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
                text: "STOP SESSION"
                enabled: sessionBridge.running
                onClicked: sessionBridge.stopSession()
            }
        }

        Item { width: 1; height: 1; Layout.fillWidth: true }

        // Row Counters
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            Text {
                text: "LOGGED: " + JSON.stringify(sessionBridge.rowCounts)
                color: Theme.muted
                font.pixelSize: 11
                font.family: "Monospace"
            }
        }

        // Emergency Stop Button integrated on ribbon
        EStopButton {
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
