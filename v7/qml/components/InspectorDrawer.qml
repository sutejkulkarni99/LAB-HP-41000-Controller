import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property bool open: false
    property string activeInstrumentId: "labhp_41000"

    width: 320
    height: parent.height
    anchors.right: parent.right
    anchors.rightMargin: open ? 0 : -width
    color: Theme.card
    border.color: Theme.border
    border.width: 1
    clip: true

    Behavior on anchors.rightMargin {
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        Row {
            width: parent.width
            Text {
                text: "INSPECTOR & TERMINAL"
                color: Theme.text
                font.pixelSize: 13
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
            Item { width: 1; height: 1; Layout.fillWidth: true }
            Button {
                text: "✕"
                onClicked: root.open = false
            }
        }

        // Instrument Target Selector
        Row {
            spacing: 6
            Button {
                text: "PSU"
                onClicked: root.activeInstrumentId = "labhp_41000"
            }
            Button {
                text: "RTB2000"
                onClicked: root.activeInstrumentId = "rtb2000"
            }
            Button {
                text: "GEN"
                onClicked: root.activeInstrumentId = "fg_edu33212a"
            }
        }

        Text {
            text: "Target: " + root.activeInstrumentId
            color: Theme.accent
            font.pixelSize: 11
            font.family: "Monospace"
        }

        // Terminal Log View
        Rectangle {
            width: parent.width
            height: parent.height - 180
            color: Theme.bg
            border.color: Theme.border
            radius: 4

            ScrollView {
                anchors.fill: parent
                anchors.margins: 8

                TextArea {
                    id: termLog
                    readOnly: true
                    text: "[SYSTEM] Ready. Enter SCPI or ASCII commands below.\n"
                    color: Theme.text
                    font.family: "Monospace"
                    font.pixelSize: 11
                    background: null
                }
            }
        }

        // Command Input Field
        Row {
            width: parent.width
            spacing: 6

            TextField {
                id: cmdInput
                width: parent.width - 70
                height: 34
                placeholderText: "Command (e.g. *IDN?, STATUS)"
                color: Theme.text
                background: Rectangle { color: Theme.bg; border.color: Theme.border; radius: 4 }
                onAccepted: sendBtn.clicked()
            }

            Button {
                id: sendBtn
                width: 64
                height: 34
                text: "SEND"
                onClicked: {
                    var c = cmdInput.text.trim();
                    if (c.length > 0) {
                        termLog.text += ">> " + c + "\n";
                        var resp = instrumentsBridge.sendRawCommand(root.activeInstrumentId, c);
                        termLog.text += "<< " + resp + "\n";
                        cmdInput.text = "";
                    }
                }
            }
        }
    }
}
