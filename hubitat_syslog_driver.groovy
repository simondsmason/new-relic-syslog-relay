/**
 * Copyright 2025 Simon Mason
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 */

/* Notes

2025-08-30 - Simon Mason
  - Version 2.01: Added destination logging to debug messages
  - Version 2.0: Updated author and namespace
  - Cleaned up code formatting

2024 - jtp10181
  - Total overhaul, check diff for all changes.

ORIGINAL staylorx VERSION: https://github.com/staylorx/hubitatCode/blob/master/drivers/Syslog.groovy

2020-08-18 - staylorx
  - A couple of dumb coding errors, and still trying to sort out TCP
2020-08-18 - staylorx
  - Received version from original author (great start!)
  - Attemping RFC5424 format for syslog
  - Date/time stamping with the hub timezone

*/

metadata {
    definition (name: "Syslog Exporter", namespace: "simonmason", author: "Simon Mason") {
        capability "Initialize"

        command "connect"
        command "disconnect"

        attribute "status", "string"
    }

    preferences {
        input("ip", "text", title: "Syslog IP Address", description: "ip address of the syslog server", required: true)
        input("port", "number", title: "Syslog IP Port", description: "syslog port", defaultValue: 514, required: true)
        input("udptcp", "enum", title: "UDP or TCP?", description: "", defaultValue: "UDP", options: ["UDP","TCP"])
        input("hostname", "text", title: "Hub Hostname", description: "hostname of the hub; leave empty for IP address")
        input("logEnable", "bool", title: "Enable debug logging", description: "", defaultValue: false)
    }
}

import groovy.json.JsonSlurper
import hubitat.device.HubAction
import hubitat.device.Protocol

void logsOff(){
    log.warn "debug logging disabled..."
    device.updateSetting("logEnable",[value:"false",type:"bool"])
}

void installed() {
    if (logEnable) log.debug "installed()"
    updated()
}

void updated() {
    if (logEnable) log.debug "updated()"
    initialize()

    //turn off debug logs after 60 minutes
    if (logEnable) runIn(3600,logsOff)
	
	if (!hostname?.trim()) {
	  def hub = location.hubs[0]
      hostname = hub.getDataValue("localIP")
    }
	hostname = hostname.replaceAll(" ", "_")
}

void parse(String description) {
      
    def descData = new JsonSlurper().parseText(description)
	
    // don't log our own messages, we will get into a loop
    def self = (descData.id.toString() == device.id.toString())

    if (self && descData.msg == "WebSocket is connected") {
        sendEvent(name:"status", value:"confirmed")
    }
	
    if(ip != null) {
        // facility = 1 (user), severity = 6 (informational)
        // priority = facility * 8 + severity = 14
        def severity = 7
        switch (descData.level) {
            case "error":
                severity = 3
                break
            case "warn":
                severity = 4
                break
            case "info":
                severity = 6
                break
            default:   //debug, trace
                severity = 7 
        }
        def priority = 8 + severity
        
        // we get date-space-time but would like ISO8601
        def dateFormat = "yyyy-MM-dd HH:mm:ss.SSS"
        def date = Date.parse(dateFormat, descData.time)
        
        // location timeZone comes from the geolocation of the hub. It's possible it's not set?
        def isoDate = date.format("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", location.timeZone)
        if (logEnable && !self) log.debug "Time we get = ${descData.time}; time we want ${isoDate}"
        
        //Get some data ready for the syslog message
        def appname = (descData.name).replaceAll(" ", ".")
        //if (appname.length() > 48) appname = appname.substring(0,48)
        def procid = descData.id.toString()
        def message = escapeStringHTMLforMsg(descData.msg)
        
        //<PRI>VERSION TIMESTAMP HOSTNAME APPNAME PROCID MSGID [DATA] MSG
        def constructedString = "<${priority}>1 ${isoDate} ${hostname} ${appname} ${procid} - - ${message}"
        if (logEnable && !self) log.debug "Sending via ${udptcp} to ${ip}:${port}: ${constructedString}"
        
        if (udptcp == 'UDP') {
            sendHubCommand(new HubAction(constructedString, Protocol.LAN, [destinationAddress: "${ip}:${port}", type: HubAction.Type.LAN_TYPE_UDPCLIENT, ignoreResponse:true]))
        } else {
            sendHubCommand(new HubAction(constructedString, Protocol.RAW_LAN, [destinationAddress: "${ip}:${port}", type: HubAction.Type.LAN_TYPE_RAW]))
        }

    } else {
        if (!self) log.warn "No syslog Server IP is set"
    }

    state.lastLogs = (new Date()).time
}

void connect() {
    if (logEnable) log.debug "attempting connection"
    runIn(60, "verifyConnection")
    runIn(7200, "checkConnection")
    try {
        interfaces.webSocket.connect("http://localhost:8080/logsocket")
    } catch(e) {
        log.error "connect error: ${e.message}"
        runIn(30, connect)
    }
}

void disconnect() {
    interfaces.webSocket.close()
}

void uninstalled() {
    disconnect()
}

void initialize() {
    if (logEnable) log.debug "initialize()"
    log.info "initializing... waiting 5 seconds before connecting to logsocket"
    runIn(60, "verifyConnection")
    runIn(5, "connect")
}

void verifyConnection() {
    if (logEnable) log.debug "checking if message was parsed after connection"
    //if (state.lastLogs + (60 * 1000) < (new Date()).time) {
    if (device.currentValue("status") != "confirmed") {
        log.info "connection message not parsed, reconnecting webSocket"
        connect()
    }
}

void checkConnection() {
    if (logEnable) log.debug "checking for parsed log recent activity"
    runIn(7200, "checkConnection")

    if (state.lastLogs + (7200 * 1000) < (new Date()).time) {
        log.info "no logs parsed recently, reconnecting webSocket"
        connect()
    }
}

void webSocketStatus(String message) {
	// handle error messages and reconnect
    if (logEnable) log.debug "webSocketStatus - ${message}"

    if (message == "status: open") {
        log.info "WebSocket is connected"
        sendEvent(name:"status", value:"connected")
        //pauseExecution(1000)
    }
    else if (message == "status: closing") {
        log.warn "WebSocket connection is closing"
        sendEvent(name:"status", value:"disconnected")
    }
    else if (message.startsWith("failure")) {
        log.warn "WebSocket failure, reconnecting"
        sendEvent(name:"status", value:"failure")
        runIn(10, connect)
    }
    else {
        log.warn "WebSocket Status unknown message, reconnecting"
        sendEvent(name:"status", value:"error")
        runIn(10, connect)
    }
}

private String escapeStringHTMLforMsg(String str) {
    if (str) {
        str = str.replaceAll("&amp;", "&")
        str = str.replaceAll("&lt;", "<")
        str = str.replaceAll("&gt;", ">")
        str = str.replaceAll("&#027;", "'")
        str = str.replaceAll("&#039;", "'") 
        str = str.replaceAll("&apos;", "'")
        str = str.replaceAll("&quot;", '"')
		str = str.replaceAll("&nbsp;", " ")
        //Strip HTML Span Tags
        str = str.replaceAll(/<\/?span.*?>/, "")
    }
    return str
}
