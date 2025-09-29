# gasera/constants.py

# PC14 and PC15 starts as inputs upon boot up, thus outputting HIGH, do not use them as output pins.
# PI16 works on armbian but marked as 'used' on debian bookworm, do not use it.

BUZZER_PIN = "PH2"

MOTOR0_CW_PIN = "PH3"
MOTOR0_CCW_PIN = "PC11"
MOTOR1_CW_PIN = "PC5"
MOTOR1_CCW_PIN = "PC8"

BOARD_IN1_PIN = "PC15"
BOARD_IN2_PIN = "PC14"
BOARD_IN3_PIN = "PH8"
BOARD_IN4_PIN = "PC7"
BOARD_IN5_PIN = "PH6"
BOARD_IN6_PIN = "PH9"

TRIGGER_PIN = "PC10"

DEFAULT_MEASUREMENT_DURATION = 600
DEBOUNCE_INTERVAL = 0.2 # seconds
MEASUREMENT_CHECK_INTERVAL = 5 # how often to check during measurement

DEFAULT_MOTOR_TIMEOUT = 10          # seconds
DEFAULT_CHART_UPDATE_DURATION = 5          # seconds