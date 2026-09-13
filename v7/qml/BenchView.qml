import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "components"

Item {
    id: root

    property bool psuConnected: false
    property bool scopeConnected: false
    property bool genConnected: false

    property real psuVoltage: 0.0
    property real psuCurrent: 0.0
    property real psuPower: 0.0
    property real psuResistance: 0.0
    property bool psuOutputOn: false

    property real scopeCh1Vrms: 0.0
    property real scopeCh1Vpp: 0.0
    property real scopeCh1Freq: 0.0
    property real scopeCh2Vrms: 0.0
    property real scopeCh2Vpp: 0.0
    property real scopeCh2Freq: 0.0

    Connections {
        target: instrumentsBridge
        function onInstrumentConnected(shortId) {
            if (shortId === "labhp_41000") root.psuConnected = true;
            if (shortId === "rtb2000") root.scopeConnected = true;
            if (shortId === "fg_edu33212a") root.genConnected = true;
        }
        function onInstrumentDisconnected(shortId) {
            if (shortId === "labhp_41000") root.psuConnected = false;
            if (shortId === "rtb2000") root.scopeConnected = false;
            if (shortId === "fg_edu33212a") root.genConnected = false;
        }
        function onTelemetryUpdated(shortId, m) {
            if (shortId === "labhp_41000") {
                root.psuVoltage = m.voltage_meas_v || 0.0;
                root.psuCurrent = m.current_meas_a || 0.0;
                root.psuPower = m.power_meas_w || 0.0;
                root.psuResistance = m.resistance_ohm || 0.0;
            } else if (shortId === "rtb2000") {
                root.scopeCh1Vrms = m.ch1_vrms || 0.0;
                root.scopeCh1Vpp = m.ch1_vpp || 0.0;
                root.scopeCh1Freq = m.ch1_freq_hz || 0.0;
                root.scopeCh2Vrms = m.ch2_vrms || 0.0;
                root.scopeCh2Vpp = m.ch2_vpp || 0.0;
                root.scopeCh2Freq = m.ch2_freq_hz || 0.0;
            }
        }
        function onStatusUpdated(shortId, s) {
            if (shortId === "labhp_41000") {
                root.psuOutputOn = s.output_on || false;
            }
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // Connection Chips Header Bar
        Row {
            width: parent.width
            spacing: 12

            ConnectionChip {
                instrumentId: "labhp_41000"
                title: "LAB-HP 41000"
                defaultResource: "127.0.0.1:10001"
                connected: root.psuConnected
            }

            ConnectionChip {
                instrumentId: "rtb2000"
                title: "R&S RTB2000"
                defaultResource: "127.0.0.1:5025"
                connected: root.scopeConnected
            }

            ConnectionChip {
                instrumentId: "fg_edu33212a"
                title: "KEYSIGHT EDU33212A"
                defaultResource: "127.0.0.1:5025"
                connected: root.genConnected
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            Button {
                text: "INSPECTOR ➔"
                onClicked: drawer.open = !drawer.open
            }
        }

        // PSU Rail
        PsuRail {
            connected: root.psuConnected
            voltageMeas: root.psuVoltage
            currentMeas: root.psuCurrent
            powerMeas: root.psuPower
            resistanceMeas: root.psuResistance
            outputOn: root.psuOutputOn
        }

        // Center Scopes Area (Responsive side-by-side or wide)
        Row {
            width: parent.width
            height: parent.height - 290
            spacing: 12

            ScopePanel {
                width: parent.width > 1200 ? (parent.width - 12) / 2 : parent.width
                height: parent.height
                connected: root.scopeConnected
                ch1Vrms: root.scopeCh1Vrms
                ch1Vpp: root.scopeCh1Vpp
                ch1Freq: root.scopeCh1Freq
                ch2Vrms: root.scopeCh2Vrms
                ch2Vpp: root.scopeCh2Vpp
                ch2Freq: root.scopeCh2Freq
            }

            ScopePanel {
                visible: parent.width > 1200
                width: (parent.width - 12) / 2
                height: parent.height
                title: "Tektronix MSO2004B (Aux)"
                instrumentId: "mso2004b"
                connected: false
            }
        }

        // Bottom Session Ribbon
        SessionRibbon {
            width: parent.width
        }
    }

    // Inspector Drawer
    InspectorDrawer {
        id: drawer
    }
}
