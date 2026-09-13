import QtQuick
import v7.qml 1.0
import ".."

Rectangle {
    id: root
    width: parent.width
    height: 44
    color: Theme.card
    border.color: Theme.border
    border.width: 1
    radius: 6

    Row {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 24

        Text {
            text: "CURSOR VALUE:"
            color: Theme.brand
            font.pixelSize: 11
            font.bold: true
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: "T = " + (archiveBridge.cursorValues.time ? archiveBridge.cursorValues.time.toFixed(3) : "0.000") + " s"
            color: Theme.text
            font.pixelSize: 12
            font.family: "Monospace"
            anchors.verticalCenter: parent.verticalCenter
        }

        Rectangle { width: 1; height: 20; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }

        Text {
            text: "PSU V: " + (archiveBridge.cursorValues["labhp_41000.voltage_meas_v"] !== undefined ? archiveBridge.cursorValues["labhp_41000.voltage_meas_v"].toFixed(2) + " V" : "--")
            color: Theme.accent
            font.pixelSize: 11
            font.family: "Monospace"
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: "PSU I: " + (archiveBridge.cursorValues["labhp_41000.current_meas_a"] !== undefined ? archiveBridge.cursorValues["labhp_41000.current_meas_a"].toFixed(3) + " A" : "--")
            color: Theme.warn
            font.pixelSize: 11
            font.family: "Monospace"
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: "SCOPE CH1: " + (archiveBridge.cursorValues["rtb2000.ch1_vrms"] !== undefined ? archiveBridge.cursorValues["rtb2000.ch1_vrms"].toFixed(2) + " Vrms" : "--")
            color: "#FACC15"
            font.pixelSize: 11
            font.family: "Monospace"
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
