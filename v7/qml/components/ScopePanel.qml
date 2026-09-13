import QtQuick
import QtQuick.Controls
import v7.qml 1.0
import ".."

Rectangle {
    id: root
    property string instrumentId: "rtb2000"
    property string title: "Rohde & Schwarz RTB2000"
    property bool connected: false
    property bool running: true
    property bool isFocused: false

    property var ch1Data: []
    property var ch2Data: []
    property var ch3Data: []
    property var ch4Data: []

    property real ch1Vrms: 0.0
    property real ch1Vpp: 0.0
    property real ch1Freq: 0.0
    property real ch2Vrms: 0.0
    property real ch2Vpp: 0.0
    property real ch2Freq: 0.0
    property string timebaseStr: "--"

    signal focusRequested()
    signal inspectorRequested(string instId)

    function format(v, unit) {
        if (v === undefined || v === null || isNaN(v) || v === "--") return "--";
        var u = unit ? (" " + unit) : "";
        return Number(v).toFixed(2) + u;
    }

    function updateWaveform(wave) {
        if (scopeScreen) {
            scopeScreen.updateWaveform(wave);
        }
    }

    function updateReadouts(values) {
        if (!values) return;
        if (values.timebase) root.timebaseStr = values.timebase;
        var ch1_rms = values.ch1_vrms !== undefined ? values.ch1_vrms : values.ch1_rms;
        var ch1_vpp = values.ch1_vpp;
        var ch1_freq = values.ch1_freq_hz !== undefined ? values.ch1_freq_hz : values.ch1_freq;
        if (ch1_rms !== undefined && !isNaN(ch1_rms)) root.ch1Vrms = Number(ch1_rms);
        if (ch1_vpp !== undefined && !isNaN(ch1_vpp)) root.ch1Vpp = Number(ch1_vpp);
        if (ch1_freq !== undefined && !isNaN(ch1_freq)) root.ch1Freq = Number(ch1_freq);

        var ch2_rms = values.ch2_vrms !== undefined ? values.ch2_vrms : values.ch2_rms;
        var ch2_vpp = values.ch2_vpp;
        var ch2_freq = values.ch2_freq_hz !== undefined ? values.ch2_freq_hz : values.ch2_freq;
        if (ch2_rms !== undefined && !isNaN(ch2_rms)) root.ch2Vrms = Number(ch2_rms);
        if (ch2_vpp !== undefined && !isNaN(ch2_vpp)) root.ch2Vpp = Number(ch2_vpp);
        if (ch2_freq !== undefined && !isNaN(ch2_freq)) root.ch2Freq = Number(ch2_freq);
    }

    color: Theme.card
    border.color: root.isFocused ? Theme.accent : Theme.border
    border.width: root.isFocused ? 2 : 1
    radius: 8

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        // Header Row (Click to toggle focus mode)
        Rectangle {
            width: parent.width
            height: 32
            color: "transparent"

            Row {
                anchors.fill: parent
                spacing: 10

                MouseArea {
                    id: headerMouse
                    anchors.verticalCenter: parent.verticalCenter
                    width: titleRow.implicitWidth + 8
                    height: 28
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.focusRequested()

                    Row {
                        id: titleRow
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8

                        Text {
                            text: root.title
                            color: Theme.text
                            font.pixelSize: 14
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Rectangle {
                            width: 50
                            height: 18
                            radius: 3
                            color: root.isFocused ? Theme.accent : Theme.border
                            visible: true
                            anchors.verticalCenter: parent.verticalCenter

                            Text {
                                anchors.centerIn: parent
                                text: root.isFocused ? "EXPANDED" : "SPLIT"
                                color: root.isFocused ? Theme.card : Theme.muted
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }
                    }
                }

                Rectangle {
                    width: 68
                    height: 24
                    radius: 4
                    color: !root.connected ? Theme.muted : (root.running ? Theme.ok : Theme.warn)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: !root.connected ? "OFFLINE" : (root.running ? "RUNNING" : "STOPPED")
                        color: Theme.card
                        font.pixelSize: 10
                        font.bold: true
                    }
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                Row {
                    spacing: 6
                    anchors.verticalCenter: parent.verticalCenter

                    Button {
                        height: 28
                        text: "RUN"
                        enabled: root.connected && !root.running
                        onClicked: {
                            root.running = true;
                            instrumentsBridge.setScopeControl(root.instrumentId, "run", 0);
                        }
                    }

                    Button {
                        height: 28
                        text: "STOP"
                        enabled: root.connected && root.running
                        onClicked: {
                            root.running = false;
                            instrumentsBridge.setScopeControl(root.instrumentId, "stop", 0);
                        }
                    }

                    Button {
                        height: 28
                        text: "SINGLE"
                        enabled: root.connected
                        onClicked: {
                            instrumentsBridge.setScopeControl(root.instrumentId, "single", 0);
                        }
                    }

                    Button {
                        height: 28
                        text: "AUTOSET"
                        enabled: root.connected
                        onClicked: {
                            instrumentsBridge.setScopeControl(root.instrumentId, "autoset", 0);
                        }
                    }

                    Button {
                        height: 28
                        text: "Inspector ⚙"
                        onClicked: root.inspectorRequested(root.instrumentId)
                    }
                }
            }
        }

        // Scope Display
        ScopeScreen {
            id: scopeScreen
            width: parent.width
            height: parent.height - 84
            connected: root.connected
            running: root.running
            ch1Data: root.ch1Data
            ch2Data: root.ch2Data
            ch3Data: root.ch3Data
            ch4Data: root.ch4Data
        }

        // Bottom Metrics & Timebase Bar
        Row {
            width: parent.width
            height: 24
            spacing: 16

            Row {
                spacing: 8
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    text: "TIMEBASE: " + (root.connected ? root.timebaseStr : "--")
                    color: Theme.muted
                    font.pixelSize: 11
                    font.family: "Monospace"
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Rectangle { width: 1; height: 16; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }

            Row {
                spacing: 16
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    text: "CH1: " + (root.connected ? (root.format(root.ch1Vrms, "Vrms") + "  |  " + root.format(root.ch1Vpp, "Vpp") + "  |  " + root.format(root.ch1Freq, "Hz")) : "--")
                    color: "#FACC15"
                    font.pixelSize: 11
                    font.family: "Monospace"
                }

                Text {
                    text: "CH2: " + (root.connected ? (root.format(root.ch2Vrms, "Vrms") + "  |  " + root.format(root.ch2Vpp, "Vpp") + "  |  " + root.format(root.ch2Freq, "Hz")) : "--")
                    color: "#38BDF8"
                    font.pixelSize: 11
                    font.family: "Monospace"
                }
            }
        }
    }
}

