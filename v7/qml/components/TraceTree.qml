import QtQuick
import QtQuick.Controls
import v7.qml 1.0
import ".."

Rectangle {
    id: root
    width: 240
    color: Theme.card
    border.color: Theme.border
    border.width: 1
    radius: 8

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        Text {
            text: "TRACE CHANNELS"
            color: Theme.text
            font.pixelSize: 12
            font.bold: true
        }

        ScrollView {
            width: parent.width
            height: parent.height - 40
            clip: true

            ListView {
                id: treeList
                width: parent.width
                model: archiveBridge.treeModel
                spacing: 10

                delegate: Column {
                    width: parent.width
                    spacing: 6

                    Text {
                        text: modelData.instrument.toUpperCase()
                        color: Theme.brand
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Repeater {
                        model: modelData.channels
                        delegate: Row {
                            spacing: 8
                            CheckBox {
                                checked: modelData.enabled
                                onCheckedChanged: {
                                    modelData.enabled = checked;
                                    archiveBridge.setChannelEnabled(modelData.instrument, [modelData.key]);
                                }
                            }
                            Text {
                                text: modelData.label
                                color: Theme.text
                                font.pixelSize: 11
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }
                }
            }
        }
    }
}
