import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "components"

Item {
    id: root

    signal inspectorRequested(string instId)

    property string focusedScope: "" // "" | "rtb2000" | "mso2004b"

    // Instruments states
    property bool psuConnected: false
    property real psuV: 0.0
    property real psuI: 0.0
    property real psuP: 0.0
    property real psuR: 0.0
    property bool psuOut: false

    property bool rtbConnected: false
    property bool rtbRunning: false
    property real rtbCh1Vrms: 0.0
    property real rtbCh1Vpp: 0.0
    property real rtbCh1Freq: 0.0
    property real rtbCh2Vrms: 0.0
    property real rtbCh2Vpp: 0.0
    property real rtbCh2Freq: 0.0
    property var rtbCh1Data: []
    property var rtbCh2Data: []

    property bool tekConnected: false
    property bool tekRunning: false
    property real tekCh1Vrms: 0.0
    property real tekCh1Vpp: 0.0
    property real tekCh1Freq: 0.0
    property real tekCh2Vrms: 0.0
    property real tekCh2Vpp: 0.0
    property real tekCh2Freq: 0.0
    property var tekCh1Data: []
    property var tekCh2Data: []

    readonly property bool isWide: root.width >= 1600

    Connections {
        target: instrumentsBridge
        function onInstrumentConnected(shortId) {
            if (shortId === "labhp_41000") root.psuConnected = true;
            else if (shortId === "rtb2000") root.rtbConnected = true;
            else if (shortId === "mso2004b") root.tekConnected = true;
        }
        function onInstrumentDisconnected(shortId) {
            if (shortId === "labhp_41000") { root.psuConnected = false; }
            else if (shortId === "rtb2000") { root.rtbConnected = false; root.rtbRunning = false; }
            else if (shortId === "mso2004b") { root.tekConnected = false; root.tekRunning = false; }
        }
        function onTelemetryUpdated(shortId, m) {
            if (shortId === "labhp_41000") {
                root.psuV = m.voltage_meas_v || 0.0;
                root.psuI = m.current_meas_a || 0.0;
                root.psuP = m.power_meas_w || 0.0;
                root.psuR = m.resistance_ohm || m.resistance_meas_ohm || 0.0;
            } else if (shortId === "rtb2000") {
                root.rtbCh1Vrms = m.ch1_vrms || 0.0;
                root.rtbCh1Vpp = m.ch1_vpp || 0.0;
                root.rtbCh1Freq = m.ch1_freq_hz || m.ch1_freq || 0.0;
                root.rtbCh2Vrms = m.ch2_vrms || 0.0;
                root.rtbCh2Vpp = m.ch2_vpp || 0.0;
                root.rtbCh2Freq = m.ch2_freq_hz || m.ch2_freq || 0.0;
            } else if (shortId === "mso2004b") {
                root.tekCh1Vrms = m.ch1_vrms || 0.0;
                root.tekCh1Vpp = m.ch1_vpp || 0.0;
                root.tekCh1Freq = m.ch1_freq_hz || m.ch1_freq || 0.0;
                root.tekCh2Vrms = m.ch2_vrms || 0.0;
                root.tekCh2Vpp = m.ch2_vpp || 0.0;
                root.tekCh2Freq = m.ch2_freq_hz || m.ch2_freq || 0.0;
            }
        }
        function onStatusUpdated(shortId, s) {
            if (shortId === "labhp_41000") {
                root.psuOut = s.output_on || false;
            } else if (shortId === "rtb2000") {
                root.rtbRunning = s.running !== undefined ? s.running : false;
            } else if (shortId === "mso2004b") {
                root.tekRunning = s.running !== undefined ? s.running : false;
            }
        }
        function onWaveformUpdated(shortId, wf) {
            var chs = wf.channels || {};
            if (shortId === "rtb2000") {
                if (chs["CH1"]) root.rtbCh1Data = chs["CH1"];
                if (chs["CH2"]) root.rtbCh2Data = chs["CH2"];
            } else if (shortId === "mso2004b") {
                if (chs["CH1"]) root.tekCh1Data = chs["CH1"];
                if (chs["CH2"]) root.tekCh2Data = chs["CH2"];
            }
        }
    }

    // 1. Bottom Ribbon (Fixed at bottom, never floats, never hides)
    SessionRibbon {
        id: sessionRibbon
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 48
    }

    // 2. PSU Rail (Fixed on left, never hidden, never becomes a tab)
    PsuRail {
        id: psuRail
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.top: parent.top
        anchors.topMargin: 8
        anchors.bottom: sessionRibbon.top
        anchors.bottomMargin: 8
        width: 280

        connected: root.psuConnected
        voltageMeas: root.psuV
        currentMeas: root.psuI
        powerMeas: root.psuP
        resistanceMeas: root.psuR
        outputOn: root.psuOut

        focusedScope: root.focusedScope
        unfocusedTitle: root.focusedScope === "rtb2000" ? "TEK MSO2004B" : "R&S RTB2000"
        unfocusedConnected: root.focusedScope === "rtb2000" ? root.tekConnected : root.rtbConnected
        unfocusedRunning: root.focusedScope === "rtb2000" ? root.tekRunning : root.rtbRunning
        unfocusedCh1Vrms: root.focusedScope === "rtb2000" ? root.tekCh1Vrms : root.rtbCh1Vrms
        unfocusedCh1Freq: root.focusedScope === "rtb2000" ? root.tekCh1Freq : root.rtbCh1Freq
        unfocusedCh2Vrms: root.focusedScope === "rtb2000" ? root.tekCh2Vrms : root.rtbCh2Vrms
        unfocusedCh2Freq: root.focusedScope === "rtb2000" ? root.tekCh2Freq : root.rtbCh2Freq

        onRestoreSplitRequested: root.focusedScope = ""
    }

    // 3. Center Area for Scopes
    Item {
        id: scopesContainer
        anchors.left: psuRail.right
        anchors.leftMargin: 8
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.top: parent.top
        anchors.topMargin: 8
        anchors.bottom: sessionRibbon.top
        anchors.bottomMargin: 8
        clip: true

        // Scope 1: R&S RTB2000
        ScopePanel {
            id: rtbPanel
            title: "R&S RTB2000"
            instrumentId: "rtb2000"
            connected: root.rtbConnected
            running: root.rtbRunning
            ch1Vrms: root.rtbCh1Vrms
            ch1Vpp: root.rtbCh1Vpp
            ch1Freq: root.rtbCh1Freq
            ch2Vrms: root.rtbCh2Vrms
            ch2Vpp: root.rtbCh2Vpp
            ch2Freq: root.rtbCh2Freq
            ch1Data: root.rtbCh1Data
            ch2Data: root.rtbCh2Data

            visible: root.focusedScope === "" || root.focusedScope === "rtb2000"

            x: 0
            y: 0
            width: {
                if (root.focusedScope === "rtb2000") return scopesContainer.width;
                if (root.isWide) return (scopesContainer.width - 8) / 2;
                return scopesContainer.width;
            }
            height: {
                if (root.focusedScope === "rtb2000") return scopesContainer.height;
                if (root.isWide) return scopesContainer.height;
                return (scopesContainer.height - 8) / 2;
            }

            onFocusRequested: {
                root.focusedScope = (root.focusedScope === "rtb2000") ? "" : "rtb2000";
            }
            onInspectorRequested: root.inspectorRequested("rtb2000")
        }

        // Scope 2: TEK MSO2004B
        ScopePanel {
            id: tekPanel
            title: "TEK MSO2004B"
            instrumentId: "mso2004b"
            connected: root.tekConnected
            running: root.tekRunning
            ch1Vrms: root.tekCh1Vrms
            ch1Vpp: root.tekCh1Vpp
            ch1Freq: root.tekCh1Freq
            ch2Vrms: root.tekCh2Vrms
            ch2Vpp: root.tekCh2Vpp
            ch2Freq: root.tekCh2Freq
            ch1Data: root.tekCh1Data
            ch2Data: root.tekCh2Data

            visible: root.focusedScope === "" || root.focusedScope === "mso2004b"

            x: {
                if (root.focusedScope === "mso2004b") return 0;
                if (root.isWide) return (scopesContainer.width + 8) / 2;
                return 0;
            }
            y: {
                if (root.focusedScope === "mso2004b") return 0;
                if (root.isWide) return 0;
                return (scopesContainer.height + 8) / 2;
            }
            width: {
                if (root.focusedScope === "mso2004b") return scopesContainer.width;
                if (root.isWide) return (scopesContainer.width - 8) / 2;
                return scopesContainer.width;
            }
            height: {
                if (root.focusedScope === "mso2004b") return scopesContainer.height;
                if (root.isWide) return scopesContainer.height;
                return (scopesContainer.height - 8) / 2;
            }

            onFocusRequested: {
                root.focusedScope = (root.focusedScope === "mso2004b") ? "" : "mso2004b";
            }
            onInspectorRequested: root.inspectorRequested("mso2004b")
        }
    }
}
