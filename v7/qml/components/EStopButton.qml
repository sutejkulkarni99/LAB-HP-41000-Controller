import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    width: 130
    height: 40
    radius: 8
    color: Theme.err
    border.color: Theme.err
    border.width: 2

    Row {
        anchors.centerIn: parent
        spacing: 6

        Text {
            text: "⛔"
            font.pixelSize: 14
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: "E-STOP"
            color: Theme.card
            font.pixelSize: 13
            font.bold: true
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            // Immediate safety cut commands
            instrumentsBridge.sendRawCommand("labhp_41000", "SB,S");
            instrumentsBridge.sendRawCommand("rtb2000", ":STOP");
            instrumentsBridge.sendRawCommand("fg_edu33212a", ":OUTPut1 0");
            instrumentsBridge.sendRawCommand("fg_edu33212a", ":OUTPut2 0");
            instrumentsBridge.sendRawCommand("mso2004b", "STOP");
        }
    }
}
