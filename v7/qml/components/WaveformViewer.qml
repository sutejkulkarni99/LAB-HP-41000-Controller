import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property string npzPath: ""
    property var waveformData: ({})

    width: parent.width
    height: 180
    color: Theme.card
    border.color: Theme.border
    border.width: 1
    radius: 8

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        Row {
            width: parent.width
            Text {
                text: "NPZ WAVEFORM INSPECTOR"
                color: Theme.text
                font.pixelSize: 12
                font.bold: true
            }
            Item { width: 1; height: 1; Layout.fillWidth: true }
            Text {
                text: root.npzPath ? root.npzPath : "No archive selected"
                color: Theme.muted
                font.pixelSize: 10
                font.family: "Monospace"
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - 40
            color: Theme.bg
            border.color: Theme.border
            radius: 4

            Canvas {
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d");
                    ctx.clearRect(0, 0, width, height);
                    ctx.strokeStyle = Theme.accent;
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();
                    for (var i = 0; i < width; ++i) {
                        var y = (height / 2) + Math.sin(i * 0.05) * (height * 0.35);
                        if (i === 0) ctx.moveTo(i, y);
                        else ctx.lineTo(i, y);
                    }
                    ctx.stroke();
                }
            }
        }
    }
}
