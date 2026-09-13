import QtQuick
import QtQuick.Controls
import v7.qml 1.0
import ".."

Rectangle {
    id: root
    property string instrumentId: ""
    property string title: "Instrument"
    property string defaultResource: "192.168.1.100:10001"
    property bool connected: false
    property bool showResource: false

    height: 32
    implicitWidth: chipRow.implicitWidth + 16
    radius: 6
    color: root.connected ? (Theme.isDark ? "#14532D" : "#DCFCE7") : Theme.card
    border.color: root.connected ? Theme.ok : Theme.border
    border.width: 1

    Row {
        id: chipRow
        anchors.centerIn: parent
        spacing: 6

        Rectangle {
            width: 8
            height: 8
            radius: 4
            anchors.verticalCenter: parent.verticalCenter
            color: root.connected ? Theme.ok : Theme.muted
        }

        Text {
            text: root.title
            color: root.connected ? (Theme.isDark ? "#86EFAC" : "#166534") : Theme.text
            font.pixelSize: 11
            font.bold: true
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            visible: root.showResource
            text: root.defaultResource
            color: Theme.muted
            font.pixelSize: 10
            font.family: "Monospace"
            anchors.verticalCenter: parent.verticalCenter
        }
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

