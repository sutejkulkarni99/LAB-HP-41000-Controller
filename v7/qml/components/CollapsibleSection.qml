import QtQuick
import QtQuick.Controls
import v7.qml 1.0
import ".."

Rectangle {
    id: root
    property string title: "Section"
    property bool expanded: true
    default property alias content: contentItem.children

    width: parent.width
    implicitHeight: header.height + (expanded ? contentItem.implicitHeight + 16 : 0)
    color: Theme.card
    border.color: Theme.border
    border.width: 1
    radius: 8
    clip: true

    Behavior on implicitHeight {
        NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
    }

    Rectangle {
        id: header
        width: parent.width
        height: 40
        color: "transparent"

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            Text {
                text: root.expanded ? "▼" : "▶"
                color: Theme.accent
                font.pixelSize: 10
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: root.title
                color: Theme.text
                font.pixelSize: 13
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.expanded = !root.expanded
        }
    }

    Item {
        id: contentItem
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 12
        visible: root.expanded
        implicitHeight: childrenRect.height
    }
}
