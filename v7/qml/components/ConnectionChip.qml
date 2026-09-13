import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property string instrumentId: ""
    property string title: "Instrument"
    property string defaultResource: "192.168.1.100:10001"
    property bool connected: false

    height: 36
    implicitWidth: chipRow.implicitWidth + 24
    radius: 8
    color: Theme.card
    border.color: connected ? Theme.ok : Theme.border
    border.width: 1

    Row {
        id: chipRow
        anchors.centerIn: parent
        spacing: 8

        Rectangle {
            width: 8
            height: 8
            radius: 4
            anchors.verticalCenter: parent.verticalCenter
            color: root.connected ? Theme.ok : Theme.muted
        }

        Text {
            text: root.title
            color: Theme.text
            font.pixelSize: 12
            font.bold: true
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: root.defaultResource
            color: Theme.muted
            font.pixelSize: 11
            font.family: "Monospace"
            anchors.verticalCenter: parent.verticalCenter
        }

        Rectangle {
            width: 54
            height: 22
            radius: 4
            color: root.connected ? Theme.err : Theme.accent
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: root.connected ? "DISC" : "CONN"
                color: Theme.card
                font.pixelSize: 10
                font.bold: true
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.connected) {
                        instrumentsBridge.disconnectInstrument(root.instrumentId);
                    } else {
                        instrumentsBridge.connectInstrument(root.instrumentId, root.defaultResource);
                    }
                }
            }
        }
    }
}
