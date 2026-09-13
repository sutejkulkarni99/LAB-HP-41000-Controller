import QtQuick
import ".."

Rectangle {
    id: root
    property var ch1Data: []
    property var ch2Data: []
    property color ch1Color: "#FACC15"
    property color ch2Color: "#38BDF8"
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

            // 1. Draw 10x8 Division Graticule Grid
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

            // 2. Draw Traces
            function drawTrace(data, strokeColor, phaseOffset) {
                ctx.strokeStyle = strokeColor;
                ctx.lineWidth = 2;
                ctx.beginPath();

                var pts = (data && data.length > 0) ? data.length : 200;
                var midY = height / 2;

                for (var p = 0; p < pts; ++p) {
                    var x = (p / (pts - 1)) * width;
                    var y = midY;
                    if (data && data.length > p) {
                        y = midY - (data[p] * 20);
                    } else {
                        // Synthetic live wave demo when empty
                        y = midY + Math.sin(p * 0.1 + phaseOffset) * (height * 0.25);
                    }
                    if (p === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                }
                ctx.stroke();
            }

            drawTrace(root.ch1Data, root.ch1Color, root.running ? (Date.now() * 0.005) : 0);
            drawTrace(root.ch2Data, root.ch2Color, root.running ? (Date.now() * 0.007 + 1.5) : 1.5);
        }
    }

    Timer {
        interval: 50
        running: root.running
        repeat: true
        onTriggered: scopeCanvas.requestPaint()
    }
}
