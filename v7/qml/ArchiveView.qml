import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "components"

Item {
    id: root

    property string sessionPath: "sessions/session_20260913_140000"

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // Top Toolbar
        Row {
            width: parent.width
            spacing: 12

            Text {
                text: "ARCHIVE & TELEMETRY REVIEW"
                color: Theme.text
                font.pixelSize: 16
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            TextField {
                id: pathInput
                width: 340
                height: 36
                text: root.sessionPath
                color: Theme.text
                background: Rectangle { color: Theme.card; border.color: Theme.border; radius: 4 }
            }

            Button {
                text: "OPEN SESSION"
                onClicked: archiveBridge.openSession(pathInput.text)
            }

            Button {
                text: "EXPORT CSV"
                onClicked: archiveBridge.exportPlot("csv", "")
            }
        }

        // Center Area: Left TraceTree + Center ArchivePlot
        Row {
            width: parent.width
            height: parent.height - 130
            spacing: 12

            TraceTree {
                height: parent.height
            }

            Column {
                width: parent.width - 252
                height: parent.height
                spacing: 10

                ArchivePlot {
                    width: parent.width
                    height: parent.height - 190
                }

                WaveformViewer {
                    width: parent.width
                    height: 180
                }
            }
        }

        // Bottom Cursor Strip
        CursorStrip {
            width: parent.width
        }
    }
}
