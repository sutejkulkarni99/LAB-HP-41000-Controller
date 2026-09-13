import QtQuick
import ".."

Rectangle {
    id: root
    property string label: "VOLTAGE"
    property string value: "0.00"
    property string unit: "V"
    property color accentColor: Theme.accent

    implicitWidth: 140
    height: 72
    color: Theme.card
    border.color: Theme.border
    border.width: 1
    radius: 8

    Column {
        anchors.centerIn: parent
        spacing: 4

        Text {
            text: root.label
            color: Theme.muted
            font.pixelSize: 10
            font.bold: true
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 4

            Text {
                text: root.value
                color: root.accentColor
                font.pixelSize: 22
                font.bold: true
                font.family: "Monospace"
            }

            Text {
                text: root.unit
                color: Theme.muted
                font.pixelSize: 13
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 2
            }
        }
    }
}
