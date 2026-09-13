import QtQuick
import v7.qml 1.0
import ".."

Rectangle {
    id: root
    property real cursorX: 0.5
    property real timeMin: 0.0
    property real timeMax: 100.0

    color: Theme.bg
    border.color: Theme.border
    border.width: 1
    radius: 8
    clip: true

    Canvas {
        id: plotCanvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            // 1. Grid Lines
            var numX = 10;
            var numY = 6;
            ctx.strokeStyle = Theme.border;
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 4]);

            for (var i = 1; i < numX; ++i) {
                var x = (i / numX) * width;
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
            }

            for (var j = 1; j < numY; ++j) {
                var y = (j / numY) * height;
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
                ctx.stroke();
            }

            // 2. Waveform Marker Overlays
            var markers = archiveBridge.waveformMarkers;
            if (markers && markers.length > 0) {
                ctx.fillStyle = Theme.warn;
                for (var m = 0; m < markers.length; ++m) {
                    var mx = (markers[m].elapsed_s / root.timeMax) * width;
                    ctx.fillRect(mx - 2, 0, 4, height);
                }
            }

            // 3. Series plotting (only when real data exists)
            // Empty state handled below if no archive loaded

            // 4. Cursor Line
            ctx.strokeStyle = Theme.brand;
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 2]);
            ctx.beginPath();
            ctx.moveTo(root.cursorX * width, 0);
            ctx.lineTo(root.cursorX * width, height);
            ctx.stroke();
        }
    }

    Text {
        anchors.centerIn: parent
        text: "No session archive loaded"
        color: Theme.muted
        font.pixelSize: 13
        font.bold: true
        visible: !archiveBridge.treeModel || archiveBridge.treeModel.length === 0
    }

    Connections {
        target: archiveBridge
        function onPlotUpdated() {
            plotCanvas.requestPaint();
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onPositionChanged: (mouse) => {
            root.cursorX = Math.max(0.0, Math.min(1.0, mouse.x / width));
            plotCanvas.requestPaint();
            var t = root.timeMin + root.cursorX * (root.timeMax - root.timeMin);
            archiveBridge.cursorMoved(t, {"time": t, "cursor_norm": root.cursorX});
        }
    }
}
