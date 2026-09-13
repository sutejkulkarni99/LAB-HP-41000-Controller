import QtQuick
import v7.qml 1.0
import ".."

Rectangle {
    id: root
    property bool connected: false
    property var timeData: []
    property var ch1Data: []
    property var ch2Data: []
    property var ch3Data: []
    property var ch4Data: []
    property bool hasSignal: false
    property color ch1Color: "#FBBF24"
    property color ch2Color: "#22C55E"
    property color ch3Color: "#3B82F6"
    property color ch4Color: "#EC4899"
    property real timebaseScale: 0.001
    property bool running: true

    function updateWaveform(wave) {
        if (!wave) return;
        root.timeData = wave.time || [];
        root.ch1Data = wave.ch1 || (wave.channels && (wave.channels["CH1"] || wave.channels["ch1"])) || [];
        root.ch2Data = wave.ch2 || (wave.channels && (wave.channels["CH2"] || wave.channels["ch2"])) || [];
        root.ch3Data = wave.ch3 || (wave.channels && (wave.channels["CH3"] || wave.channels["ch3"])) || [];
        root.ch4Data = wave.ch4 || (wave.channels && (wave.channels["CH4"] || wave.channels["ch4"])) || [];
        root.hasSignal = (root.timeData && root.timeData.length > 0) ||
                         (root.ch1Data && root.ch1Data.length > 0) ||
                         (root.ch2Data && root.ch2Data.length > 0);
        scopeCanvas.requestPaint();
    }

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

            // 2. Traces or Empty State
            if (root.hasSignal) {
                var channels = [
                    { data: root.ch1Data, color: root.ch1Color },
                    { data: root.ch2Data, color: root.ch2Color },
                    { data: root.ch3Data, color: root.ch3Color },
                    { data: root.ch4Data, color: root.ch4Color }
                ];

                var minVal = Infinity;
                var maxVal = -Infinity;
                var hasAnyPoints = false;

                for (var c = 0; c < channels.length; ++c) {
                    var arr = channels[c].data;
                    if (arr && arr.length > 0) {
                        hasAnyPoints = true;
                        for (var k = 0; k < arr.length; ++k) {
                            var v = arr[k];
                            if (v < minVal) minVal = v;
                            if (v > maxVal) maxVal = v;
                        }
                    }
                }

                if (hasAnyPoints) {
                    if (minVal === Infinity || maxVal === -Infinity) {
                        minVal = -1;
                        maxVal = 1;
                    } else if (maxVal === minVal) {
                        minVal -= 1;
                        maxVal += 1;
                    } else {
                        var span = maxVal - minVal;
                        minVal -= span * 0.05;
                        maxVal += span * 0.05;
                    }

                    var minT = Infinity;
                    var maxT = -Infinity;
                    if (root.timeData && root.timeData.length > 0) {
                        minT = root.timeData[0];
                        maxT = root.timeData[root.timeData.length - 1];
                        if (minT > maxT) { var tmp = minT; minT = maxT; maxT = tmp; }
                    }
                    var hasTimeSpan = (minT !== Infinity && maxT !== -Infinity && maxT > minT);

                    var padY = 8;
                    var availH = height - (2 * padY);

                    for (var c = 0; c < channels.length; ++c) {
                        var d = channels[c].data;
                        if (!d || d.length === 0) continue;
                        ctx.strokeStyle = channels[c].color;
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        var pts = d.length;
                        for (var p = 0; p < pts; ++p) {
                            var normX = (hasTimeSpan && root.timeData && p < root.timeData.length)
                                ? (root.timeData[p] - minT) / (maxT - minT)
                                : (pts > 1 ? (p / (pts - 1)) : 0.5);
                            var normY = (d[p] - minVal) / (maxVal - minVal);
                            var sx = normX * width;
                            var sy = padY + (1.0 - normY) * availH;
                            if (p === 0) {
                                ctx.moveTo(sx, sy);
                            } else {
                                ctx.lineTo(sx, sy);
                            }
                        }
                        ctx.stroke();
                    }
                }
            } else {
                ctx.fillStyle = Theme.muted;
                ctx.font = "bold 13px sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText("No signal — connect instrument", width / 2, height / 2);
            }
        }
    }

    onCh1DataChanged: scopeCanvas.requestPaint()
    onCh2DataChanged: scopeCanvas.requestPaint()
    onCh3DataChanged: scopeCanvas.requestPaint()
    onCh4DataChanged: scopeCanvas.requestPaint()
    onConnectedChanged: scopeCanvas.requestPaint()
    onHasSignalChanged: scopeCanvas.requestPaint()
}

