import QtQuick
import v7.qml 1.0
import ".."

Rectangle {
    id: root
    property bool connected: false
    property var ch1Data: []
    property var ch2Data: []
    property var ch3Data: []
    property var ch4Data: []
    property color ch1Color: "#FACC15"
    property color ch2Color: "#38BDF8"
    property color ch3Color: "#F43F5E"
    property color ch4Color: "#4ADE80"
    property real timebaseScale: 0.001
    property bool running: true

    color: Theme.bg
    border.color: Theme.border
    border.width: 1
    radius: 6
    clip: true

    Canvas {
        id: scopeCanvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            // 1. Draw 10x8 Division Graticule Grid (always rendered)
            var xDivs = 10;
            var yDivs = 8;
            var dx = width / xDivs;
            var dy = height / yDivs;

            ctx.strokeStyle = Theme.border;
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 4]);

            for (var i = 1; i < xDivs; ++i) {
                ctx.beginPath();
                ctx.moveTo(i * dx, 0);
                ctx.lineTo(i * dx, height);
                ctx.stroke();
            }

            for (var j = 1; j < yDivs; ++j) {
                ctx.beginPath();
                ctx.moveTo(0, j * dy);
                ctx.lineTo(width, j * dy);
                ctx.stroke();
            }

            // Center crosshairs
            ctx.setLineDash([]);
            ctx.strokeStyle = Theme.muted;
            ctx.lineWidth = 1;

            ctx.beginPath();
            ctx.moveTo(0, height / 2);
            ctx.lineTo(width, height / 2);
            ctx.stroke();

            ctx.beginPath();
            ctx.moveTo(width / 2, 0);
            ctx.lineTo(width / 2, height);
            ctx.stroke();

            // 2. Draw Traces ONLY from real arrays pushed via bridge
            if (root.connected) {
                function drawTrace(data, strokeColor) {
                    if (!data || data.length === 0) return;
                    ctx.strokeStyle = strokeColor;
                    ctx.lineWidth = 2;
                    ctx.beginPath();

                    var pts = data.length;
                    var midY = height / 2;

                    for (var p = 0; p < pts; ++p) {
                        var x = (p / (pts - 1)) * width;
                        var y = midY - (data[p] * 20);
                        if (p === 0) {
                            ctx.moveTo(x, y);
                        } else {
                            ctx.lineTo(x, y);
                        }
                    }
                    ctx.stroke();
                }

                drawTrace(root.ch1Data, root.ch1Color);
                drawTrace(root.ch2Data, root.ch2Color);
                drawTrace(root.ch3Data, root.ch3Color);
                drawTrace(root.ch4Data, root.ch4Color);
            }
        }
    }

    onCh1DataChanged: scopeCanvas.requestPaint()
    onCh2DataChanged: scopeCanvas.requestPaint()
    onCh3DataChanged: scopeCanvas.requestPaint()
    onCh4DataChanged: scopeCanvas.requestPaint()
    onConnectedChanged: scopeCanvas.requestPaint()

    // Empty state overlay for unconnected scopes or when no trace lines are present
    Item {
        anchors.centerIn: parent
        visible: !root.connected || (!root.ch1Data.length && !root.ch2Data.length && !root.ch3Data.length && !root.ch4Data.length)

        Text {
            anchors.centerIn: parent
            text: "No signal — connect instrument"
            color: Theme.muted
            font.pixelSize: 13
            font.bold: true
        }
    }
}

