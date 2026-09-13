import QtQuick
import QtQuick.Controls
import v7.qml 1.0
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
                id: wfCanvas
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d");
                    ctx.clearRect(0, 0, width, height);

                    // Grid
                    ctx.strokeStyle = Theme.border;
                    ctx.lineWidth = 1;
                    ctx.setLineDash([2, 4]);
                    for (var gx = 1; gx < 8; ++gx) {
                        ctx.beginPath();
                        ctx.moveTo((gx / 8) * width, 0);
                        ctx.lineTo((gx / 8) * width, height);
                        ctx.stroke();
                    }
                    for (var gy = 1; gy < 4; ++gy) {
                        ctx.beginPath();
                        ctx.moveTo(0, (gy / 4) * height);
                        ctx.lineTo(width, (gy / 4) * height);
                        ctx.stroke();
                    }

                    // Only draw if real samples exist in waveformData
                    var samples = root.waveformData && root.waveformData.samples ? root.waveformData.samples : [];
                    if (samples && samples.length > 0) {
                        ctx.setLineDash([]);
                        ctx.strokeStyle = Theme.accent;
                        ctx.lineWidth = 1.5;
                        ctx.beginPath();
                        for (var i = 0; i < samples.length && i < width; ++i) {
                            var px = (i / samples.length) * width;
                            var py = (height / 2) - samples[i] * 20;
                            if (i === 0) ctx.moveTo(px, py);
                            else ctx.lineTo(px, py);
                        }
                        ctx.stroke();
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                text: "No waveform data loaded"
                color: Theme.muted
                font.pixelSize: 11
                visible: !root.waveformData || !root.waveformData.samples || root.waveformData.samples.length === 0
            }
        }
    }
}
