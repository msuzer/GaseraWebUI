# gasera/constants.py

TRIGGER_PIN = "PC10" # "PC1"
BUZZER_PIN = "PH2"

MOTOR0_CW_PIN = "PH3"
MOTOR0_CCW_PIN = "PC11"
MOTOR1_CW_PIN = "PC5" # "PC15"
MOTOR1_CCW_PIN = "PC8" # "PC14"

BUTTON0_PIN = "PC15"
BUTTON1_PIN = "PC14"
BUTTON2_PIN = "PH8"
BUTTON3_PIN = "PC7"

MOTOR0_LIMIT_PIN = "PH6" # "PI6"
MOTOR1_LIMIT_PIN = "PH9" # "PC8"
# MOTOR1_LIMIT_PIN = "PI16" # PI16 works on armbian but marked as 'used' on debian bookworm, so switching to PC8

DEFAULT_MEASUREMENT_DURATION = 600
DEBOUNCE_INTERVAL = 0.2 # seconds
MEASUREMENT_CHECK_INTERVAL = 5 # how often to check during measurement

DEFAULT_MOTOR_TIMEOUT = 10          # seconds
DEFAULT_CHART_UPDATE_DURATION = 5          # seconds