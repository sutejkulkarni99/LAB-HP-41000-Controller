import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "components"

Item {
    id: root

    property string protocolPath: "protocols/power_step_test.yaml"
    property bool running: false
    property int currentStep: -1
    property string statusMessage: "No protocol running. Load a YAML protocol to begin."

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // Header and Controls
        Row {
            width: parent.width
            spacing: 12

            Text {
                text: "AUTOMATED PROTOCOL RUNNER"
                color: Theme.text
                font.pixelSize: 16
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            TextField {
                id: pathInput
                width: 320
                height: 36
                text: root.protocolPath
                color: Theme.text
                background: Rectangle { color: Theme.card; border.color: Theme.border; radius: 4 }
            }

            Button {
                text: "PREVIEW"
                onClicked: root.statusMessage = "Protocol loaded. Ready to run."
            }

            Button {
                text: root.running ? "ABORT" : "RUN PROTOCOL"
                enabled: true
                onClicked: {
                    root.running = !root.running;
                    if (root.running) {
                        root.currentStep = 0;
                        root.statusMessage = "Executing Step 1: Ramp Voltage...";
                        stepTimer.start();
                    } else {
                        stepTimer.stop();
                        root.statusMessage = "Protocol execution aborted.";
                    }
                }
            }
        }

        // Live Step Progress & Indicator
        Rectangle {
            width: parent.width
            height: 72
            color: Theme.card
            border.color: Theme.border
            border.width: 1
            radius: 8

            Row {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 24

                Rectangle {
                    width: 10
                    height: 10
                    radius: 5
                    color: root.running ? Theme.ok : Theme.muted
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: root.statusMessage
                    color: Theme.text
                    font.pixelSize: 13
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                Text {
                    text: root.running ? ("STEP " + (root.currentStep + 1) + " / 4") : "IDLE"
                    color: Theme.accent
                    font.pixelSize: 13
                    font.bold: true
                    font.family: "Monospace"
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // Steps Definition & Verification Table
        Rectangle {
            width: parent.width
            height: parent.height - 180
            color: Theme.card
            border.color: Theme.border
            border.width: 1
            radius: 8

            Column {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "EXECUTION SEQUENCE"
                    color: Theme.muted
                    font.pixelSize: 11
                    font.bold: true
                }

                ListView {
                    width: parent.width
                    height: parent.height - 40
                    spacing: 8
                    clip: true

                    model: ListModel {
                        ListElement { stepName: "1. Baseline PSU Initialization"; inst: "labhp_41000"; cmd: "UA,24.0; SB,R"; duration: "2.0s" }
                        ListElement { stepName: "2. RTB2000 Autoscale & Trigger Edge"; inst: "rtb2000"; cmd: ":AUT; :TRIG:A:MODE AUTO"; duration: "1.5s" }
                        ListElement { stepName: "3. Voltage Ramp Step (48V Load)"; inst: "labhp_41000"; cmd: "UA,48.0; IA,5.0"; duration: "5.0s" }
                        ListElement { stepName: "4. Fast Waveform Dump & Standby"; inst: "labhp_41000"; cmd: "SB,S"; duration: "1.0s" }
                    }

                    delegate: Rectangle {
                        width: parent.width
                        height: 48
                        radius: 6
                        color: (root.currentStep === index && root.running) ? Theme.cardHover : Theme.bg
                        border.color: (root.currentStep === index && root.running) ? Theme.accent : Theme.border
                        border.width: 1

                        Row {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 16

                            Text {
                                text: stepName
                                color: Theme.text
                                font.pixelSize: 12
                                font.bold: true
                                width: 260
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: "[" + inst + "]"
                                color: Theme.brand
                                font.pixelSize: 11
                                width: 120
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: cmd
                                color: Theme.muted
                                font.pixelSize: 11
                                font.family: "Monospace"
                                width: 280
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Item { width: 1; height: 1; Layout.fillWidth: true }

                            Text {
                                text: duration
                                color: Theme.accent
                                font.pixelSize: 11
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }
                }
            }
        }
    }

    Timer {
        id: stepTimer
        interval: 2500
        repeat: true
        onTriggered: {
            root.currentStep++;
            if (root.currentStep >= 4) {
                stepTimer.stop();
                root.running = false;
                root.statusMessage = "Protocol sequence finished successfully.";
            } else {
                root.statusMessage = "Executing Step " + (root.currentStep + 1) + "...";
            }
        }
    }
}
