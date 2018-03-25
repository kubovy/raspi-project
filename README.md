# Raspberry Pi Zero Alphabot 2 Controll System

## MQTT API

The general convention of the topics follows the following format: `{service}/[state|control]/[module]/#`

Every state change SHOULD be accompanied by a `{service}/state/#` message published to the broker.

### Overview
  | Topic                                      | Type | Payload                                    | Description                                                             |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/status`                   | PUB  | `OPEN`/`CLOSED`                            | Node's connection is `OPEN` or `CLOSED`                                 |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/buzzer`                   | PUB  | `ON`/`OFF`                                 | Buzzer is `ON` or `OFF`                                                 |
  | `{service}/control/buzzer`                 | SUB  | `ON`/`OFF`                                 | Sets buzzer `ON` or `OFF`                                               |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/servo/{servo}/raw`        | PUB  | _RAW_                                      | The _RAW_ value of a servo's state                                      |
  | `{service}/state/servo/{servo}/percent`    | PUB  | _PERCENT_                                  | The _PERCENT_ value of a servo's state                                  |
  | `{service}/control/camera/{servo}[/{type}]`| SUB  | Integer                                    | Sets the servo's position as `type` (`pecent`, `degrees` or _RAW_)      |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/ir-receiver/state`        | PUB  | `ON`/`OFF`                                 | IR receiver's listening state is `ON` or `OFF`                          |
  | `{service}/state/ir-receiver/control`      | PUB  | `ON`/`OFF`                                 | IR receiver control state is `ON` or `OFF`                              |
  | `{service}/state/ir-receiver/key`          | PUB  | Integer                                    | Received key code form the IR remote control                            |
  | `{service}/control/ir-receiver/state`      | SUB  | `ON`/`OFF`/`CONTROL`                       | Sets the IR receiver's listening state `ON`, `OFF` or in `CONTROL` mode |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/ir-sensor/state`          | PUB  | `ON`/`OFF`                                 | IR sensors listening state is `ON` or `OFF`                             |
  | `{service}/state/ir-sensor/{id}`           | PUB  | `OPEN`/`CLOSED`                            | IR sensor with `id` is `OPEN` or `CLOSED`                               |
  | `{service}/control/ir-sensor/state`        | SUB  | `ON`/`OFF`                                 | Sets the IR sensors listening state `ON` or `OFF`                       |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/joystick/state`           | PUB  | `ON`/`OFF`                                 | Joystick's listening state is `ON` or `OFF`                             |
  | `{service}/state/joystick/button`          | PUB  | `NONE`/`UP`/`DOWN`/`RIGHT`/`LEFT`/`CENTER` | Joystick's position                                                     |
  | `{service}/state/joystick/center`          | PUB  | `OPEN`/`CLOSED`                            | Joystick's center state                                                 |
  | `{service}/state/joystick/up`              | PUB  | `OPEN`/`CLOSED`                            | Joystick's up state                                                     |
  | `{service}/state/joystick/right`           | PUB  | `OPEN`/`CLOSED`                            | Joystick's right state                                                  |
  | `{service}/state/joystick/down`            | PUB  | `OPEN`/`CLOSED`                            | Joystick's down state                                                   |
  | `{service}/state/joystick/left`            | PUB  | `OPEN`/`CLOSED`                            | Joystick's left state                                                   |
  | `{service}/state/joystick/control`         | PUB  | `OFF`/`MOVEMENT`/`CAMERA`                  | Joystick's control state                                                |
  | `{service}/control/joystick/state`         | SUB  | `ON`/`OFF`                                 | Sets the Joystick's listening state `ON` or `OFF`                       |
  | `{service}/control/joystick/control`       | SUB  | `OFF`/`MOVEMENT`/`CAMERA`                  | Sets the Joystick's control state.                                      |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/motion`                   | PUB  | `OPEN`/`CLOSED`                            | Motion detected (`OPEN`) or no motion detected (`CLOSED`)               |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/led/{pixel}`              | PUB  | `R,G,B`                                    | Color of for particular `PIXEL`                                         |
  | `{service}/control/led[/{pixel}]`          | SUB  | `R,G,B`/`R,G,B,PIXEL`                      | Sets a color for particular `PIXEL`                                     |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/rgb/`                     | PUB  | `R,G,B`                                    | Color ot the led strip                                                  |
  | `{service}/control/rgb/`                   | SUB  | `R,G,B`                                    | Set the led strip's color.                                              |
  | `{service}/control/rgb/{pattern}`          | SUB  | `R,G,B,step,intrerval`                     |                                                                         |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/tracking`                 | PUB  | `ON`/`OFF`                                 |                                                                         |
  | `{service}/state/tracking`                 | PUB  | `MEASURE`                                  |                                                                         |
  | `{service}/state/tracking/delay`           | PUB  | Integer                                    |                                                                         |
  | `{service}/control/tracking`               | SUB  | `ON`/`OFF`                                 |                                                                         |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/ultrasonic/state`         | PUB  | `ON`/`OFF`                                 |                                                                         |
  | `{service}/state/ultrasonic`               | PUB  | `MEASURE`                                  |                                                                         |
  | `{service}/state/ultrasonic/delay`         | PUB  | Integer                                    |                                                                         |
  | `{service}/control/ultrasonic/state`       | SUB  | `ON`/`OFF`                                 |                                                                         |
  | ------------------------------------------ | ---- | ------------------------------------------ | ----------------------------------------------------------------------- |
  | `{service}/state/move`                     | PUB  | `LEFT RIGHT TIMEOUT`                       |                                                                         |
  | `{service}/control/move/[direction]`       | SUB  | `SPEED TIMEOUT`                            |                                                                         |
  | `{service}/control/rotate/[direction]`     | SUB  | `SPEED TIMEOUT`                            |                                                                         |
  | `{service}/control/turn/[direction]`       | SUB  | `SPEED TIMEOUT`                            |                                                                         |
  | `{service}/control/stop`                   | SUB  |                                            |                                                                         |


### General

* `{service}/state/status`

  is triggered when the node gets online (`ON`) or offline (`OFF`). This topic is also published with the payload `OFF` 
  as the robot's _last will_.

### Buzzer

This module controls the buzzer and responds to `{service}/control/buzzer/#` topic messages.

*  `{service}/state/buzzer`

  is triggered when the buzzer state changes between on `ON` and `OFF` state.

* `{service}/control/buzzer`

  turns the buzzer `ON` or `OFF`.

### Servos

* `{service}/state/servo/[servo]/raw`

  is triggered when the servos position is changed. Payload is the _RAW_ value of the servo's state. The `[servo]` is a
  sequence starting with `0` identifying a concrete servo.
                                   

* `{service}/state/servo/[servo]/percent`

  is triggered when the servo's position is changed. Payload is the _PERCENTAGE_ value of the servo's state
  between the defined _minumum_ and _maximum_ value defined for each servo separately. The _minimum_ value equals `0`%,
  _maximum_ value equals `100`%. The `[servo]` is a sequence starting with `0` identifying a concrete servo.

* `{service}/control/servo/[servo]/[type]`

  controls the servo's position. If the value `type` is `percent` then the _minimum_ value is `0`%, _maximum_
  value is `100`%. If the value `type` is `degrees` then the _minimum_ value is `-90`° and the _maximum_ value
  is `90`°. If the value `type` is `raw` then the _minimum_ and _maximum_ values depend on the servo.
  If the value `type` is something else or missing in the topic path the `raw` `type` is assumed.

  | `type`              | Description             |
  | ------------------- | ----------------------- |
  | `deg`               | Payload in degrees      |
  | `percent`           | Payload in percent      |
  | `raw` or _NOTHING_  | Payload as _RAW_ value  |

### IR Receiver

* `{service}/state/ir-receiver/state`

    is triggered when the IR listening state changes between `ON` and `OFF` state.

* `{service}/state/ir-receiver/control`

    is triggered when the IR controlling state changes between `ON` and `OFF` states.

* `{service}/state/ir-receiver/key`

    is triggered when IR code is received. The payload is the received IR code.

* `{service}/control/ir-receiver/state`

    changes the state of the IR receiver between `ON`, `OFF` and `CONTROL` state.

### IR Sensor

* `{service}/state/ir-sensor/state`

   is triggered when the IR sensors listening state changes between `ON` and `OFF` state.

* `{service}/control/ir-sensor/{id}`

   is triggered when a IR sensor with `id` changes state between `OPEN` and `CLOSED` 

* `{service}/state/ir/control`

   changes the listening state of the IR sensors between `ON` and `OFF`.

### Joystick

* `{service}/state/joystick/state`

  is triggered when the joystick's listening state state changes between `ON` and `OFF`.

* `{service}/state/joystick/button`

  is triggered when the joystick's state changes.

  | Payload   | Description       |
  | --------- | ----------------- |
  | `NONE`    | Default position  |
  | `UP`      | Pushed up         |
  | `DOWN`    | Pushed down       |
  | `RIGHT`   | Pushed right      |
  | `LEFT`    | Pushed left       |
  | `CENTER`  | Center pushed     |


* `{service}/state/joystick/center`

  is triggered when the joystick's center state changes between `OPEN` and `CLOSED`.

* `{service}/state/joystick/up`

  is triggered when the joystick's up state changes between `OPEN` and `CLOSED`.

* `{service}/state/joystick/right`

  is triggered when the joystick's right state changes between `OPEN` and `CLOSED`.

* `{service}/state/joystick/down`

  is triggered when the joystick's down state changes between `OPEN` and `CLOSED`.

* `{service}/state/joystick/left`

  is triggered when the joystick's left state changes between `OPEN` and `CLOSED`.

* `{service}/state/joystick/control`

  is triggered when the joystick's control state changes.

  | Payload   | Description                               |
  | --------- | ----------------------------------------- |
  | `OFF`     | Joystick's control state is disabled      |
  | `CAMERA`  | Joystick is controlling the camera servos |
  | `MOVEMENT`| Joystick is controlling the movement      |


* `{service}/control/joystick/state`

  set the listening state of the joystick `ON` or `OFF`.

* `{service}/control/joystick/control`

  set the control state of the joystick

  | Payload    | Description                                   |
  | ---------- | --------------------------------------------- |
  | `NONE`     | Disables joystick's control state             |
  | `CAMERA`   | Enables joystick to control the camera servos |
  | `MOVEMANT` | Enables joystick is control the movement      |
  
### Motion Detector

* `{service}/state/motion`

### Pixels

* `{service}/state/led/[pixel]`

  is triggered when a pixel led changes color.

* `{service}/control/led`

  sets a color for multiple pixel. The different pixel configurations are separated by space and each
  entry has 4 values separated by comma in the format: `R,G,B,PIXEL`.

* `{service}/control/led/[pixel]`

  sets a color for particular `pixel`. The payload has 3 values separated by comma in the format: `R,G,B`.

### RGB Strip

* `[service_name]/state/rgb`

  is triggered when the RGB strip light configuration changes. The payload contains the settings in the format: 
  `R,G,B`, e.g., `255,0,0` for full red color

* `[service_name]/control/rgb`

  sets the color on the strip. Payload should be in the format: `R,G,B`, e.g., `255,0,0` for full red color

* `[service_name]/control/rgb/[pattern]`

  sets a color with a pattern. The following patterns are supported:

  * `fade-in` will fade in from black to defined color. The payload is in the following format: `[R],[G],[B],[step],[interval]` where:

    |              |                                              |
    | ------------ | -------------------------------------------- |
    | `[R]`        | Red color from `0` to `255`                  |
    | `[G]`        | Green color from `0` to `255`                |
    | `[B]`        | Blue color from `0` to `255`                 |
    | `[step]`     | Fading step in percent between `1` and `100`, if not set `5`% is used as default.  |
    | `[interval]` | Interval in ms to wait between fading steps, if not set `50`ms is used as default. |

  * `fade-out` will fade in from the defined color to black. The payload is in the following format: `[R],[G],[B],[step],[interval]` where:

    |              |                                              |
    | ------------ | -------------------------------------------- |
    | `[R]`        | Red color from `0` to `255`                  |
    | `[G]`        | Green color from `0` to `255`                |
    | `[B]`        | Blue color from `0` to `255`                 |
    | `[step]`     | Fading step in percent between `1` and `100`, if not set `5`% is used as default.  |
    | `[interval]` | Interval in ms to wait between fading steps, if not set `50`ms is used as default. |

### Tracking Sensor

* `{service}/state/tracking/state`
* `{service}/state/tracking`
* `{service}/state/tracking/delay`
* `{service}/control/tracking/state`

### Ultrasonic Sensor

* `{service}/state/ultrasonic/state`
* `{service}/state/ultrasonic`
* `{service}/state/ultrasonic/delay`
* `{service}/control/ultrasonic/state`

### Wheels

* `{service}/state/move`
* `{service}/state/move/left`
* `{service}/state/move/right`
* `{service}/control/move/[direction]`
* `{service}/control/rotate/[direction]`
* `{service}/control/turn/[direction]`
* `{service}/control/stop`

